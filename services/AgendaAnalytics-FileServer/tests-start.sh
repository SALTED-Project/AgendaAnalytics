#! /usr/bin/env bash
set -e

cd /app
python ./backend_pre_start.py

pytest --rootdir=/app --order-dependencies -v --junitxml=/tmp/test_result.xml ./tests 