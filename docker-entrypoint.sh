#!/bin/bash
set -e

# Create necessary directories
mkdir -p /app/data/scan /app/data/sorted /app/logs /app/temp

# Wait for any dependencies if needed
echo "Starting Document Sorter application..."

# Run database migrations or setup if needed
# python setup.py

# Start the application
exec "$@"