#!/bin/bash

# Activate the NeSy_KR conda environment and start the server

# Initialize conda
eval "$(conda shell.bash hook)"
conda activate NeSy_KR

# Change to the project root so Python can find the 'api' module
cd "$(dirname "$0")/.."

# Start the server
python -m api.server "$@"
