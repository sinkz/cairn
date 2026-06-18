#!/usr/bin/env sh
set -eu

REPO="${CAIRN_REPO:-sinkz/cairn}"
VERSION="${CAIRN_VERSION:-latest}"
INSTALL_DIR="${CAIRN_INSTALL_DIR:-$HOME/.local/bin}"
RELEASES_URL="https://github.com/${REPO}/releases"

# Expected release assets:
# - cairn-linux-x64.tar.gz
# - cairn-linux-arm64.tar.gz
# - cairn-macos-x64.tar.gz
# - cairn-macos-arm64.tar.gz

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: $1 is required." >&2
    exit 1
  fi
}

detect_asset() {
  os="$(uname -s)"
  arch="$(uname -m)"

  case "$os" in
    Linux)
      platform="linux"
      ;;
    Darwin)
      platform="macos"
      ;;
    *)
      echo "ERROR: unsupported operating system: $os" >&2
      exit 1
      ;;
  esac

  case "$arch" in
    x86_64|amd64)
      cpu="x64"
      ;;
    arm64|aarch64)
      cpu="arm64"
      ;;
    *)
      echo "ERROR: unsupported architecture: $arch" >&2
      exit 1
      ;;
  esac

  printf "cairn-%s-%s.tar.gz" "$platform" "$cpu"
}

download_base() {
  if [ "$VERSION" = "latest" ]; then
    printf "%s/latest/download" "$RELEASES_URL"
    return
  fi

  case "$VERSION" in
    v*) tag="$VERSION" ;;
    *) tag="v$VERSION" ;;
  esac
  printf "%s/download/%s" "$RELEASES_URL" "$tag"
}

verify_checksum() {
  asset="$1"
  checksum_file="$2"

  if ! grep "  $asset\$" "$checksum_file" > "$checksum_file.one"; then
    echo "ERROR: checksum for $asset was not found in checksums.txt." >&2
    exit 1
  fi

  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c "$checksum_file.one"
    return
  fi

  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c "$checksum_file.one"
    return
  fi

  echo "ERROR: sha256sum or shasum is required." >&2
  exit 1
}

need curl
need tar

ASSET="$(detect_asset)"
BASE_URL="$(download_base)"
TMP_DIR="${TMPDIR:-/tmp}/cairn-install-$$"
ARCHIVE="$TMP_DIR/$ASSET"
CHECKSUMS="$TMP_DIR/checksums.txt"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

mkdir -p "$TMP_DIR"
mkdir -p "$INSTALL_DIR"

echo "Downloading $ASSET from $BASE_URL"
curl -fsSL "$BASE_URL/$ASSET" -o "$ARCHIVE"
curl -fsSL "$BASE_URL/checksums.txt" -o "$CHECKSUMS"

(
  cd "$TMP_DIR"
  verify_checksum "$ASSET" "$CHECKSUMS"
  tar -xzf "$ARCHIVE"
)

if [ ! -f "$TMP_DIR/cairn" ]; then
  echo "ERROR: release archive did not contain a cairn binary." >&2
  exit 1
fi

cp "$TMP_DIR/cairn" "$INSTALL_DIR/cairn"
chmod 755 "$INSTALL_DIR/cairn"

case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "NOTE: $INSTALL_DIR is not currently in PATH."
    echo "Add this to your shell profile:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
    ;;
esac

"$INSTALL_DIR/cairn" --version
echo "Installed Cairn at $INSTALL_DIR/cairn"
