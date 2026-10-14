//! Unix domain socket IPC for communication between the Edgepad daemon and GUI.
//!
//! Provides a non-blocking IPC server in the daemon and allows the GUI to:
//! - Monitor daemon status in real time
//! - Stream live gesture and slider events for the Live Gesture Tester
//! - Enable or disable Test Mode (safe simulation)
//! - Trigger configuration reloads

use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

pub const DEFAULT_SOCKET_NAME: &str = "edgepad.sock";

/// Returns the standard Unix socket path for Edgepad.
pub fn default_ipc_socket_path() -> PathBuf {
    if let Some(runtime_dir) = env::var_os("XDG_RUNTIME_DIR").filter(|v| !v.is_empty()) {
        PathBuf::from(runtime_dir).join("edgepad").join(DEFAULT_SOCKET_NAME)
    } else {
        let uid = unsafe { libc::getuid() };
        PathBuf::from(format!("/tmp/edgepad-{uid}")).join(DEFAULT_SOCKET_NAME)
    }
}

/// Shared broadcaster that can send JSON events to all connected clients.
#[derive(Clone, Default, Debug)]
pub struct IpcBroadcaster {
    clients: Arc<Mutex<Vec<UnixStream>>>,
}

impl IpcBroadcaster {
    pub fn new() -> Self {
        Self::default()
    }

    /// Broadcast a JSON message line to all active clients.
    pub fn broadcast(&self, message: &str) {
        let mut msg = message.to_string();
        if !msg.ends_with('\n') {
            msg.push('\n');
        }

        let mut clients = match self.clients.lock() {
            Ok(guard) => guard,
            Err(_) => return,
        };

        let mut alive = Vec::new();
        for mut client in clients.drain(..) {
            if client.write_all(msg.as_bytes()).is_ok() {
                let _ = client.flush();
                alive.push(client);
            }
        }
        *clients = alive;
    }

    fn add_client(&self, client: UnixStream) {
        if let Ok(mut clients) = self.clients.lock() {
            // Set short write timeout so a stuck client doesn't block broadcasts
            let _ = client.set_write_timeout(Some(Duration::from_millis(50)));
            clients.push(client);
        }
    }
}

/// Command handler callback type for processing requests from GUI clients.
pub type CommandHandler = Arc<dyn Fn(&str) -> Option<String> + Send + Sync>;

/// IPC server that listens for connections and dispatches commands.
pub struct IpcServer {
    socket_path: PathBuf,
    stop: Arc<AtomicBool>,
    broadcaster: IpcBroadcaster,
}

impl IpcServer {
    pub fn start(
        socket_path: PathBuf,
        broadcaster: IpcBroadcaster,
        handler: CommandHandler,
    ) -> Result<Self, String> {
        if let Some(parent) = socket_path.parent() {
            let _ = fs::create_dir_all(parent);
        }

        // Clean up any stale socket file
        if socket_path.exists() {
            let _ = fs::remove_file(&socket_path);
        }

        let listener = UnixListener::bind(&socket_path)
            .map_err(|err| format!("failed to bind IPC socket {}: {err}", socket_path.display()))?;
        listener
            .set_nonblocking(true)
            .map_err(|err| format!("failed to set nonblocking on IPC socket: {err}"))?;

        let stop = Arc::new(AtomicBool::new(false));
        let stop_clone = stop.clone();
        let bcast_clone = broadcaster.clone();
        let sock_path_clone = socket_path.clone();

        thread::Builder::new()
            .name("edgepad-ipc".to_string())
            .spawn(move || {
                run_ipc_listener_loop(listener, stop_clone, bcast_clone, handler);
                let _ = fs::remove_file(&sock_path_clone);
            })
            .map_err(|err| format!("failed to spawn IPC thread: {err}"))?;

        Ok(Self {
            socket_path,
            stop,
            broadcaster,
        })
    }

    pub fn broadcaster(&self) -> &IpcBroadcaster {
        &self.broadcaster
    }

    pub fn socket_path(&self) -> &Path {
        &self.socket_path
    }
}

impl Drop for IpcServer {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::SeqCst);
        let _ = fs::remove_file(&self.socket_path);
    }
}

fn run_ipc_listener_loop(
    listener: UnixListener,
    stop: Arc<AtomicBool>,
    broadcaster: IpcBroadcaster,
    handler: CommandHandler,
) {
    while !stop.load(Ordering::SeqCst) {
        match listener.accept() {
            Ok((stream, _)) => {
                let _ = stream.set_read_timeout(Some(Duration::from_millis(100)));
                let broadcaster_clone = broadcaster.clone();
                let handler_clone = handler.clone();
                let stop_conn = stop.clone();

                thread::spawn(move || {
                    handle_ipc_connection(stream, broadcaster_clone, handler_clone, stop_conn);
                });
            }
            Err(ref e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                thread::sleep(Duration::from_millis(50));
            }
            Err(_) => {
                thread::sleep(Duration::from_millis(100));
            }
        }
    }
}

fn handle_ipc_connection(
    stream: UnixStream,
    broadcaster: IpcBroadcaster,
    handler: CommandHandler,
    stop: Arc<AtomicBool>,
) {
    let read_stream = match stream.try_clone() {
        Ok(s) => s,
        Err(_) => return,
    };
    broadcaster.add_client(stream);

    let mut reader = BufReader::new(read_stream);
    let mut line = String::new();

    while !stop.load(Ordering::SeqCst) {
        line.clear();
        match reader.read_line(&mut line) {
            Ok(0) => break, // Client disconnected
            Ok(_) => {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }
                if let Some(response) = handler(trimmed) {
                    broadcaster.broadcast(&response);
                }
            }
            Err(ref e)
                if e.kind() == std::io::ErrorKind::WouldBlock
                    || e.kind() == std::io::ErrorKind::TimedOut =>
            {
                continue;
            }
            Err(_) => break,
        }
    }
}
