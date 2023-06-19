#!/bin/bash -e

PROJECT_ROOT="$(dirname "${BASH_SOURCE[0]}")/.."

echo "Applying any and all code formatters."

cd "${PROJECT_ROOT}"

set -x

black ./omada ./tests ./examples
ruff check --fix ./omada ./tests ./examples