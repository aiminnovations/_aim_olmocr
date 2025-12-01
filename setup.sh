#!/bin/bash
#
# olmOCR One-Click Setup
#
# This is the main entry point for installing olmOCR.
# It runs the automated installer that handles everything.
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/installer/setup.sh" "$@"
