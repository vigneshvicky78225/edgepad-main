use edgepad::config::{DeviceConfig, EdgepadConfig, GestureActionConfig};
use edgepad::core::{GestureDirection, SliderAxis, Zone};

#[test]
fn release_example_config_parses_and_uses_axis_appropriate_gestures() {
    let config = EdgepadConfig::parse(include_str!("../examples/edgepad.toml.example"))
        .expect("release example config should parse");

    assert_eq!(config.device, DeviceConfig::Auto);
    assert_eq!(config.gestures.len(), 8);
    assert_eq!(config.sliders.len(), 2);

    for slider in &config.sliders {
        assert!(
            matches!(slider.zone, Zone::Left | Zone::Right),
            "release example sliders should use side zones: {slider:?}"
        );
        assert_eq!(slider.axis, SliderAxis::Vertical);
        assert!(!slider.negative.argv().unwrap().is_empty());
        assert!(!slider.positive.argv().unwrap().is_empty());
    }

    for binding in &config.gestures {
        match binding.zone {
            Zone::Left | Zone::Right => {
                assert!(
                    matches!(binding.direction, GestureDirection::Tap),
                    "side zones with sliders should only use tap gestures: {binding:?}"
                );
            }
            Zone::Top => {
                assert!(
                    matches!(
                        binding.direction,
                        GestureDirection::Left
                            | GestureDirection::Right
                            | GestureDirection::Tap
                            | GestureDirection::DoubleTap
                    ),
                    "top examples should use horizontal or tap gestures: {binding:?}"
                );
            }
            Zone::Bottom => {
                assert!(
                    matches!(
                        binding.direction,
                        GestureDirection::Left | GestureDirection::Right
                    ),
                    "bottom examples should use horizontal gestures: {binding:?}"
                );
            }
            Zone::TopLeft | Zone::TopRight | Zone::BottomLeft | Zone::BottomRight => {
                assert!(
                    matches!(binding.direction, GestureDirection::DoubleTap),
                    "corner zones should only use double-tap gestures: {binding:?}"
                );
            }
        }
        assert!(
            matches!(binding.action, GestureActionConfig::Command { .. }),
            "example gestures should run command argv actions: {binding:?}"
        );
    }
}

#[test]
fn release_udev_rules_use_uaccess_for_touchpad_and_uinput() {
    let rules = include_str!("../packaging/70-edgepad.rules");

    assert!(rules.contains(r#"ENV{ID_INPUT_TOUCHPAD}=="1""#));
    assert!(rules.contains(r#"TAG+="uaccess""#));
    assert!(rules.contains(r#"KERNEL=="uinput""#));
    assert!(rules.contains(r#"OPTIONS+="static_node=uinput""#));
}

#[test]
fn release_user_service_runs_installed_user_binary_with_config() {
    let service = include_str!("../packaging/edgepad.service");

    assert!(
        service.contains("ExecStart=/usr/bin/edgepad daemon"),
        "service was: {service}"
    );
    assert!(
        !service.contains("/home/vicky"),
        "service must not contain developer paths"
    );
    assert!(
        !service.contains("%h/.local/bin"),
        "service must not hardcode user local bin"
    );
    assert!(service.contains("WantedBy=default.target"));
    assert!(service.contains("Restart=on-failure"));
    assert!(service.contains("RestartSec=2s"));
    assert!(service.contains("Type=notify"));
    assert!(service.contains("NotifyAccess=main"));
    assert!(service.contains("TimeoutStartSec=45s"));
    assert!(service.contains("ExecReload=/usr/bin/kill -HUP $MAINPID"));
}

#[test]
fn packaging_and_spec_standardize_on_system_paths() {
    let spec = include_str!("../packaging/edgepad.spec");

    assert!(spec.contains("%{_bindir}/edgepad"));
    assert!(spec.contains("%{_datadir}/edgepad/edgepad.toml"));
    assert!(spec.contains("%{_userunitdir}/edgepad.service"));
    assert!(spec.contains("%{_udevrulesdir}/70-edgepad.rules"));
    assert!(!spec.contains("/home/vicky"));
    assert!(!spec.contains("%h/.local/bin"));

    let desktop = include_str!("../packaging/org.edgepad.Edgepad.desktop");
    assert!(desktop.contains("Exec=edgepad gui"));
    assert!(!desktop.contains("/home/vicky"));
}

#[test]
fn packaging_rpm_verifies_packaged_files_and_no_developer_paths() {
    let rpm_matches = glob_rpm_files();
    if let Some(rpm_path) = rpm_matches.first() {
        let output = std::process::Command::new("rpm")
            .args(["-qlp", &rpm_path.display().to_string()])
            .output();
        if let Ok(out) = output {
            let files = String::from_utf8_lossy(&out.stdout);
            assert!(files.contains("/usr/bin/edgepad"));
            assert!(files.contains("/usr/lib/systemd/user/edgepad.service"));
            assert!(files.contains("/usr/lib/udev/rules.d/70-edgepad.rules"));
            assert!(files.contains("/usr/share/applications/org.edgepad.Edgepad.desktop"));
            assert!(files.contains("/usr/share/edgepad/edgepad.toml"));
            assert!(files.contains("/usr/share/edgepad/gui/main.py"));
            assert!(
                !files.contains("/home/vicky"),
                "RPM must not contain developer paths"
            );
        }
    }
}

fn glob_rpm_files() -> Vec<std::path::PathBuf> {
    let dir = std::path::Path::new("rpmbuild/RPMS");
    let mut results = Vec::new();
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_dir() {
                if let Ok(sub) = std::fs::read_dir(&p) {
                    for s in sub.flatten() {
                        let sp = s.path();
                        if sp.extension().map(|e| e == "rpm").unwrap_or(false) {
                            results.push(sp);
                        }
                    }
                }
            }
        }
    }
    results
}

#[test]
fn release_workflow_publishes_required_assets_and_checksums() {
    let workflow = include_str!("../.github/workflows/release.yml");

    for required in [
        "edgepad-x86_64-unknown-linux-musl",
        "70-edgepad.rules",
        "edgepad.service",
        "edgepad.toml.example",
        "checksums",
        "Verify tag matches Cargo version",
        "v$PACKAGE_VERSION",
        "gh release create",
        "--generate-notes",
        "targets: x86_64-unknown-linux-musl",
        "--target x86_64-unknown-linux-musl",
        "readelf -l",
        "INTERP",
    ] {
        assert!(
            workflow.contains(required),
            "release workflow should mention {required}"
        );
    }
}

#[test]
fn ci_uses_the_locked_dependency_graph_for_rust_checks() {
    let workflow = include_str!("../.github/workflows/ci.yml");

    assert!(workflow.contains("cargo clippy --locked --all-targets -- -D warnings"));
    assert!(workflow.contains("cargo test --locked"));
}
