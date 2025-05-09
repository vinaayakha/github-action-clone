#!/bin/bash

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run Gunicorn with the following configuration:
# - 4 worker processes
# - Uvicorn worker class for ASGI support
# - Bind to all interfaces on port 8000
# - Enable auto-reload for development
# - Set timeout to 120 seconds
# - Enable access logging
gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --reload \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info 