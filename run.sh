#!/bin/bash

# OpenAI API Proxy startup script using uv

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copying from .env.example"
    cp .env.example .env
    echo "Please edit .env file with your OpenAI API key before running the service."
    exit 1
fi

# Add common uv installation paths to PATH
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Check if uv is installed
if ! which uv >/dev/null 2>&1; then
    echo "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
else
    echo "uv is already installed."
fi

# Sync dependencies with uv
echo "Syncing dependencies with uv..."
uv sync

# Run the service
echo "Starting OpenAI API Proxy service..."
uv run python start.py