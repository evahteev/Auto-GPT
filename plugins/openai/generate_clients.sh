#!/bin/bash

# Find all openapi.yaml files in the current directory and its subdirectories
files_found=$(find . -name "openapi.yaml")

# Check if any openapi.yaml files were found
if [ -z "$files_found" ]; then
    echo "Error: No openapi.yaml files found in the current directory or its subdirectories."
    exit 1
fi

# Iterate through all openapi.yaml files found and generate clients
for file_path in $files_found; do
    echo "Processing: $file_path"

    # Get the directory containing the openapi.yaml file
    file_dir=$(dirname "$file_path")

    # Generate the Python client from the openapi.yaml file
    openapi-python-client generate --path "$file_path"

    # Check if the client was successfully generated
    if [ $? -eq 0 ]; then
        echo "Python client successfully generated for: $file_path"

        # Move the generated client into the subdirectory containing the openapi.yaml file
        client_dir=$(grep -oP '(?<=packageName: ).*' "$file_path" | tr -d '\r')
        mv "$client_dir" "$file_dir/"
    else
        echo "Error: Failed to generate Python client for: $file_path"
        exit 1
    fi

    echo ""
done