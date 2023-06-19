#!/bin/bash

# Re-install the (mounted) package in editable mode
# pip install -e 
SETUP_DIR=$(readlink -f "$(dirname "${BASH_SOURCE[0]}")/../..")
poetry install --sync

poetry shell