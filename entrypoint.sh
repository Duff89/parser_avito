#!/bin/bash

# Workaround for the first request timing out in podman
wait_seconds=1
echo "Waiting for $wait_seconds seconds..."
sleep $wait_seconds
cd /app
python parser_cls.py
