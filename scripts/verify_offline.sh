#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -m compileall -q pinky_line_alignment tests
PYTHONPATH=. python3 -m pytest -q
PYTHONPATH=. python3 -m pinky_line_alignment.offline_demo --output /tmp/pinky_alignment_preview.png
PYTHONPATH=. python3 -m pinky_line_alignment.closed_loop_sim
printf '\nOFFLINE checks passed. No ROS 2 robot motion was attempted.\n'
