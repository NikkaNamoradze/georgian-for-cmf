#!/usr/bin/env bash
# Builds build/JX402_V1.0.0.73_georgian.bin from the stock CMF Watch Pro 2 firmware.
# Needs: git, uv (https://docs.astral.sh/uv/). Nothing here talks to a watch.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/build"
UTILS="$BUILD/cmf-watch-utils"
UTILS_REPO="https://github.com/fmctools/cmf-watch-utils.git"
UTILS_COMMIT="7997d40f93136ce4c03cd3452ccce9bdd2d0dcab"
STOCK="$BUILD/JX402_V1.0.0.73.bin"
STOCK_URL="https://media.githubusercontent.com/media/fmctools/cmf-watch-utils/main/dumps/binaries/firmware/JX402_V1.0.0.73.bin"
STOCK_SHA256="30903fc8ce6db4f8860bb554366635db3d2bcbb2d43827b3b50fbbac22b59353"
OUT="$BUILD/JX402_V1.0.0.73_georgian.bin"
PY=(uv run -q --no-project --with pillow==13.0.0 python)
# The firmware images in that repo are Git LFS files; skip them (works without git-lfs installed).
NOLFS=(-c filter.lfs.smudge= -c filter.lfs.process= -c filter.lfs.required=false)

mkdir -p "$BUILD"

if [ ! -d "$UTILS/.git" ]; then
  echo "==> Fetching cmf-watch-utils"
  git "${NOLFS[@]}" clone -q --filter=blob:limit=2m "$UTILS_REPO" "$UTILS"
fi
git -C "$UTILS" "${NOLFS[@]}" -c advice.detachedHead=false checkout -q "$UTILS_COMMIT"

if [ ! -f "$STOCK" ]; then
  echo "==> Downloading stock firmware 1.0.0.73"
  curl -fL --progress-bar -o "$STOCK.part" "$STOCK_URL"
  mv "$STOCK.part" "$STOCK"
fi
echo "$STOCK_SHA256  $STOCK" | shasum -a 256 -c - >/dev/null \
  || { echo "Stock firmware checksum mismatch: delete $STOCK and retry" >&2; exit 1; }

echo "==> Extracting the notification font"
rm -rf "$BUILD/unpacked" "$BUILD/fonts"
(cd "$UTILS" && uv run -q fwkit unpack "$STOCK" "$BUILD/unpacked" >/dev/null \
  && uv run -q fwkit sdfs-extract "$BUILD/unpacked/raw/fonts.bin.bin" "$BUILD/fonts" >/dev/null)

echo "==> Adding Georgian letters"
"${PY[@]}" "$ROOT/tools/patch_font.py" "$BUILD/fonts/sans32.font" "$ROOT/fonts/NotoSansGeorgian.ttf" "$BUILD/sans32_ka.font"
"${PY[@]}" "$ROOT/tools/preview.py" "$BUILD/sans32_ka.font" "$BUILD/preview.png"

echo "==> Rebuilding the firmware package"
rm -f "$OUT"
(cd "$UTILS" && uv run -q fwkit edit-sdfs "$STOCK" fonts.bin sans32.font "$BUILD/sans32_ka.font" "$OUT" >/dev/null \
  && uv run -q fwkit verify "$OUT" >/dev/null)

echo
echo "Built:   $OUT"
echo "SHA-256: $(shasum -a 256 "$OUT" | cut -d' ' -f1)"
echo "Preview: $BUILD/preview.png"
