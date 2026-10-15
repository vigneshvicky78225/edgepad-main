%global debug_package %{nil}

Name:           edgepad
Version:        0.2.5
Release:        1%{?dist}
Summary:        Native Linux Touchpad Edge Gesture Manager

License:        MIT OR Apache-2.0
URL:            https://github.com/assembledev/edgepad
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  cargo
BuildRequires:  rust >= 1.70.0
BuildRequires:  python3-devel
BuildRequires:  systemd-rpm-macros

Requires:       python3
Requires:       python3-pyside6
Requires:       systemd
Requires:       libevdev

%description
Edgepad transforms touchpad edge swipes into native Linux hardware control gestures.
With native Qt 6 / QML integration for Fedora KDE Plasma on Wayland, users can
configure brightness, volume, and desktop controls with fine-tuned sensitivity
and zero terminal interaction.

%prep
%autosetup -n %{name}-%{version}

%build
# Ensure cargo from rustup or system is found in PATH
export PATH="$HOME/.cargo/bin:$PATH"
cargo build --offline --release --locked

%install
# Install main Rust binary
install -Dpm 0755 target/release/edgepad %{buildroot}%{_bindir}/edgepad

# Install GUI components
install -d %{buildroot}%{_datadir}/edgepad/gui
cp -a gui/* %{buildroot}%{_datadir}/edgepad/gui/
chmod 0755 %{buildroot}%{_datadir}/edgepad/gui/main.py

# Install desktop entry
install -Dpm 0644 packaging/org.edgepad.Edgepad.desktop %{buildroot}%{_datadir}/applications/org.edgepad.Edgepad.desktop

# Install AppStream metadata
install -Dpm 0644 packaging/org.edgepad.Edgepad.metainfo.xml %{buildroot}%{_metainfodir}/org.edgepad.Edgepad.metainfo.xml

# Install desktop icon
install -Dpm 0644 packaging/icons/org.edgepad.Edgepad.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/org.edgepad.Edgepad.svg

# Install systemd user service (adjust path for system install)
install -d %{buildroot}%{_userunitdir}
sed 's|%h/\.local/bin/edgepad|%{_bindir}/edgepad|g' packaging/edgepad.service > %{buildroot}%{_userunitdir}/edgepad.service
chmod 0644 %{buildroot}%{_userunitdir}/edgepad.service

# Install udev rules for touchpad and uinput permissions
install -Dpm 0644 packaging/70-edgepad.rules %{buildroot}%{_udevrulesdir}/70-edgepad.rules

# Install default config example
install -Dpm 0644 examples/edgepad.toml.example %{buildroot}%{_datadir}/edgepad/edgepad.toml.example

%post
%systemd_user_post edgepad.service
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :

%postun
%systemd_user_postun edgepad.service
if [ $1 -eq 0 ] ; then
    /bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    %{_bindir}/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi

%files
%license LICENSE-MIT LICENSE-APACHE
%doc README.md
%{_bindir}/edgepad
%{_datadir}/edgepad/
%{_datadir}/applications/org.edgepad.Edgepad.desktop
%{_metainfodir}/org.edgepad.Edgepad.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/org.edgepad.Edgepad.svg
%{_userunitdir}/edgepad.service
%{_udevrulesdir}/70-edgepad.rules

%changelog
* Wed Oct 14 2026 Edgepad Team <edgepad@example.org> - 0.2.5-1
- Initial release with native Qt 6 QML GUI and uinput virtual keyboard backend
