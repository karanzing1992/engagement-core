#!/bin/sh
# Reproduce a local, redistribution-compatible Tabler stylesheet without charts/CDNs.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
(cd "$tmp" && npm pack @tabler/core@1.7.0 --ignore-scripts --silent >/dev/null)
archive="$tmp/tabler-core-1.7.0.tgz"
expected="9de5840569dbb946989b4870f4bf02f3570369cccb5ecbfa34c76477d29a16fa"
actual=$(sha256sum "$archive" | cut -d' ' -f1)
if [ "$actual" != "$expected" ]; then
    echo "Tabler archive checksum mismatch; refusing to bundle." >&2
    exit 1
fi
mkdir -p "$here/assets/css"
tar -xOzf "$archive" package/dist/css/tabler.min.css > "$here/assets/css/tabler.min.css"
printf 'Bundled Tabler 1.7.0 MIT CSS: %s bytes\n' "$(wc -c < "$here/assets/css/tabler.min.css")"

