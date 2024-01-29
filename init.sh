#!/bin/bash
set -e

echo "Starting SSH ..."
service ssh start

cd /app
python app.py
