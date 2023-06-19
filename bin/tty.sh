#!/bin/bash

THIS_DIR=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))
cd "${THIS_DIR}/.."
exec docker compose run --service-ports --rm dev_container