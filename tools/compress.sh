#!/usr/bin/env bash
set -euo pipefail

# Directory containing source videos (relative to repository root)
SRC_DIR="$(git rev-parse --show-toplevel)/web/media"

# Ensure ffmpeg is available
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found in PATH. Please install ffmpeg before running this script." >&2
  exit 1
fi

# Header for size table
printf "%s\t%s\t%s\t%s\n" "Original file" "Original size" "Compressed file" "Compressed size"

# Process each video file in the source directory
shopt -s nullglob
for src in "$SRC_DIR"/*.{mp4,mkv,avi,webm,mov}; do
  # Skip if no matching files
  [ -e "$src" ] || continue

  # Derive output filename
  base="$(basename "$src")"
  name="${base%.*}"
  out="$SRC_DIR/${name}_compressed.mp4"

  # Run ffmpeg: trim to 60s, scale to 480p height, encode H.264 with target bitrate ~300k
  ffmpeg -y -i "$src" \
    -t 60 \
    -vf "scale=-2:480" \
    -c:v libx264 -preset veryslow -b:v 300k -maxrate 300k -bufsize 600k \
    -c:a aac -b:a 64k \
    -movflags +faststart \
    "$out" >/dev/null 2>&1

  # Gather sizes (human readable)
  orig_size=$(du -h "$src" | cut -f1)
  comp_size=$(du -h "$out" | cut -f1)

  printf "%s\t%s\t%s\t%s\n" "$base" "$orig_size" "${name}_compressed.mp4" "$comp_size"

done

shopt -u nullglob
