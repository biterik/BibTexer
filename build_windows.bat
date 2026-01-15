@echo off
REM Build script for Windows

echo Building BibTexer for Windows...

REM Install dependencies
pip install -r requirements.txt

REM Get customtkinter path
for /f "tokens=*" %%i in ('python -c "import customtkinter; print(customtkinter.__path__[0])"') do set CTK_PATH=%%i

REM Build with PyInstaller
pyinstaller --onefile ^
    --windowed ^
    --name "BibTexer" ^
    --add-data "%CTK_PATH%;customtkinter" ^
    bibtexer_gui.py

echo Build complete! Executable is in dist\BibTexer.exe
pause
