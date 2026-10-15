#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

VERSION="$(grep '^version =' Cargo.toml | head -n1 | cut -d'"' -f2)"
RPMBUILD_DIR="${REPO_ROOT}/rpmbuild"

echo "==> Building Edgepad v${VERSION} RPM package for Fedora..."

# 1. Vendor dependencies offline if not already present
if [ ! -d "vendor" ]; then
    echo "==> Vendoring cargo crates..."
    cargo vendor vendor
fi

mkdir -p .cargo
cat << 'EOF' > .cargo/config.toml
[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "vendor"
EOF

# 2. Setup rpmbuild directory tree
mkdir -p "${RPMBUILD_DIR}"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

# 3. Create clean source archive
echo "==> Creating source tarball edgepad-${VERSION}.tar.gz..."
tar --exclude-vcs \
    --exclude='./target' \
    --exclude='./rpmbuild' \
    -czf "${RPMBUILD_DIR}/SOURCES/edgepad-${VERSION}.tar.gz" \
    --transform "s,^\.,edgepad-${VERSION}," .

# 4. Copy spec file
cp "${SCRIPT_DIR}/edgepad.spec" "${RPMBUILD_DIR}/SPECS/"

# 5. Build binary and source RPMs
echo "==> Running rpmbuild..."
rpmbuild -ba --nodeps \
    --define "_topdir ${RPMBUILD_DIR}" \
    "${RPMBUILD_DIR}/SPECS/edgepad.spec"

echo ""
echo "==> RPM build complete!"
echo "Binary RPM: $(find "${RPMBUILD_DIR}/RPMS" -name "*.rpm")"
echo "Source RPM: $(find "${RPMBUILD_DIR}/SRPMS" -name "*.src.rpm")"
