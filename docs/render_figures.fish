#!/usr/bin/env fish

# Set the directory containing the diagrams
set FIGURES_DIR docs/figures

# Check if plantuml is installed
if not type -q plantuml
    echo "Error: plantuml is not installed or not in PATH."
    exit 1
end

echo "Building PlantUML diagrams in $FIGURES_DIR..."

# Find all .puml files in the directory and process them
for puml_file in $FIGURES_DIR/*.puml
    echo "Processing $puml_file..."
    plantuml -tpng $puml_file
    if test $status -eq 0
        echo "Successfully generated PNG for $puml_file"
    else
        echo "Failed to generate PNG for $puml_file"
    end
end

echo "All diagrams processed."

