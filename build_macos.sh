#!/bin/bash
# Build script for macOS

echo "Building BibTexer for macOS..."

# Install dependencies
pip install -r requirements.txt

# Build with PyInstaller - include core module
pyinstaller --onefile \
    --windowed \
    --name "BibTexer" \
    --add-data "$(python -c 'import customtkinter; print(customtkinter.__path__[0])'):customtkinter" \
    --hidden-import bibtexer_core \
    bibtexer_gui.py

echo "Build complete! App is in dist/BibTexer.app"
