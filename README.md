# BibTexer

A cross-platform tool that converts DOIs to complete BibTeX entries using the CrossRef API.

![BibTexer GUI](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![License](https://img.shields.io/badge/License-AGPL--3.0-green)
![Python](https://img.shields.io/badge/Python-3.6%2B-yellow)

## Features

- 🔍 Fetches publication metadata from CrossRef API
- 📝 Generates properly formatted BibTeX entries
- 🎨 Modern GUI with dark/light mode support
- 💻 Cross-platform: Windows, macOS, and Linux
- 📋 Automatic clipboard copy
- 🔧 Command-line interface also available
- ✨ Automatically determines entry type (article, inproceedings, book, etc.)
- 🔑 Creates citation keys from first author's name and publication year
- 🛡️ Escapes special LaTeX characters

## GUI Version

### Running from Source

```bash
# Clone the repository
git clone https://github.com/biterik/BibTexer.git
cd BibTexer

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python bibtexer_gui.py
```

### Building Standalone Executables

#### macOS
```bash
chmod +x build_macos.sh
./build_macos.sh
# Output: dist/BibTexer.app
```

#### Windows
```batch
build_windows.bat
# Output: dist\BibTexer.exe
```

#### Linux
```bash
chmod +x build_linux.sh
./build_linux.sh
# Output: dist/BibTexer
```

## Command-Line Version

### Installation

```bash
git clone https://github.com/biterik/BibTexer.git
cd BibTexer
chmod +x doi2bib.py
```

### Usage

```bash
./doi2bib.py <doi>
```

### Examples

```bash
# Using plain DOI
./doi2bib.py 10.1038/nature12373

# Using full DOI URL
./doi2bib.py https://doi.org/10.1038/nature12373

# Using doi: prefix
./doi2bib.py doi:10.1038/nature12373
```

### Sample Output

```bibtex
@article{kucsko2013,
  author = {Kucsko, G. and Maurer, P. C. and Yao, N. Y. and Kubo, M. and Noh, H. J. and Lo, P. K. and Park, H. and Lukin, M. D.},
  title = {Nanometre-scale thermometry in a living cell},
  journal = {Nature},
  year = {2013},
  month = aug,
  volume = {500},
  number = {7460},
  pages = {54--58},
  publisher = {Springer Science and Business Media LLC},
  doi = {10.1038/nature12373},
  url = {https://doi.org/10.1038/nature12373},
  issn = {0028-0836}
}
```

## Requirements

### For running from source:
- Python 3.6+
- customtkinter (GUI version)

### For clipboard support:
- **macOS**: Built-in (uses `pbcopy`)
- **Windows**: Built-in (uses `clip`)
- **Linux**: `xclip` or `xsel` (install with `sudo apt install xclip`)

## Project Structure

```
BibTexer/
├── bibtexer_gui.py    # GUI application
├── doi2bib.py         # Command-line tool
├── requirements.txt   # Python dependencies
├── build_macos.sh     # macOS build script
├── build_windows.bat  # Windows build script
├── build_linux.sh     # Linux build script
├── LICENSE            # AGPL-3.0 license
└── README.md          # This file
```

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Author

Erik Bitzek

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
