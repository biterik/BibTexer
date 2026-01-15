#!/bin/bash
# Build script for Linux

echo "Building BibTexer for Linux..."

# Install dependencies
pip install -r requirements.txt

# Build with PyInstaller
pyinstaller --onefile \
    --windowed \
    --name "BibTexer" \
    --add-data "$(python -c 'import customtkinter; print(customtkinter.__path__[0])'):customtkinter" \
    bibtexer_gui.py

echo "Build complete! Executable is in dist/BibTexer"
