#!/bin/bash

echo "--- Straight outta commits installer. ---"

if ! command -v python3 &> /dev/null
then
    echo "Error: python3 is not installed. Please install Python 3."
    exit 1
fi

echo "Creating Python virtual environment 'gitcredvenv'..."
python3 -m venv gitcredvenv
source gitcredvenv/bin/activate

echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies."
    exit 1
fi
source gitcredvenv/bin/activate
python gitcred_cli.py --help
