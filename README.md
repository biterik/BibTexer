# BibTexer

A cross-platform tool to convert DOIs and references to BibTeX entries, and download papers via Open Access or institutional access.

**Part of the [MatWerk Scholar Toolbox](https://nfdi-matwerk.de/) - Developed within [NFDI-MatWerk](https://nfdi-matwerk.de/)**

![BibTexer GUI](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![License](https://img.shields.io/badge/License-AGPL--3.0-green)
![Python](https://img.shields.io/badge/Python-3.6%2B-yellow)
![Version](https://img.shields.io/badge/Version-2.2.1-brightgreen)
[![NFDI-MatWerk](https://img.shields.io/badge/NFDI-MatWerk-orange)](https://nfdi-matwerk.de/)

## Features

### Core Features
- 🔍 **DOI Lookup**: Direct conversion from DOI to BibTeX
- 🔎 **Reference Search**: Find papers by author, title, journal, year - no DOI needed!
- 📄 **Open Access**: Download free PDFs via Unpaywall (arXiv, bioRxiv, repositories)
- 🏛️ **Journal Access**: Open publisher page for institutional/subscription access
- 📝 **Complete BibTeX**: Generates properly formatted entries with all metadata
- 📋 **Clipboard Support**: Automatic copy to clipboard on all platforms
- ✨ **Smart Entry Types**: Automatically determines @article, @inproceedings, @book, etc.
- 🔑 **Citation Keys**: Auto-generates keys from first author + year
- 🛡️ **LaTeX Safe**: Escapes special characters for LaTeX compatibility

### Reference Search (New in v2.0!)
Search CrossRef using partial reference information:
- **Author citations**: `G. Thomas and M. J. Whelan, Phil. Mag. 4, 511 (1959)`
- **Journal references**: `PHYSICAL REVIEW MATERIALS 5, 083603 (2021)`  
- **Title search**: `Kinetic Theory of Dislocation Climb. I. General Models...`
- Intelligently parses authors, year, journal, volume, and page numbers
- Includes database of common journal abbreviations
- Shows selection dialog when multiple matches are found

### GUI Features
- 🎨 Modern interface with dark/light mode
- 💻 Cross-platform: Windows, macOS, and Linux
- 📑 Tabbed interface for DOI lookup and reference search
- 🖱️ One-click paper access: Open Access (Unpaywall) or Journal (institutional)

## Installation

### Download Pre-built Installers (Recommended)

Download the latest release for your platform from the [Releases page](https://github.com/biterik/BibTexer/releases/latest):

| Platform | Download | Notes |
|----------|----------|-------|
| **Windows** | `BibTexer-Windows-x86_64.exe` | Double-click to run |
| **macOS (Apple Silicon)** | `BibTexer-macOS-AppleSilicon.app.zip` | For M1/M2/M3 Macs |
| **macOS (Intel)** | `BibTexer-macOS-Intel.app.zip` | For older Intel Macs |
| **Linux** | `BibTexer-Linux-x86_64` | Make executable: `chmod +x BibTexer-Linux-x86_64` |

#### macOS Installation Notes
1. Download and unzip the `.app.zip` file
2. Move `BibTexer.app` to your Applications folder
3. On first launch, right-click → "Open" to bypass Gatekeeper (since the app is not notarized)

### From Source

If you prefer to run from source or want to contribute:

```bash
# Clone the repository
git clone https://github.com/biterik/BibTexer.git
cd BibTexer

# Install dependencies (for GUI)
pip install -r requirements.txt

# Run the GUI
python bibtexer_gui.py

# Or use the CLI
chmod +x doi2bib.py  # Unix/macOS only
./doi2bib.py <doi>
```

### Requirements (Source Installation)
- Python 3.6+
- customtkinter (installed via requirements.txt)

## Usage

### GUI Application

Launch BibTexer from your Applications folder, Start Menu, or run:

```bash
python bibtexer_gui.py
```

The GUI provides two tabs:
1. **DOI Lookup**: Enter a DOI to get its BibTeX entry
2. **Reference Search**: Enter any citation information to search CrossRef

### Command Line

```bash
# DOI lookup
./doi2bib.py <doi>

# Reference search
./doi2bib.py --search "<reference>"

# Download/open paper
./doi2bib.py --open <doi>
```

#### CLI Examples

```bash
# DOI lookup - plain DOI
./doi2bib.py 10.1038/nature12373

# DOI lookup - full URL
./doi2bib.py https://doi.org/10.1038/nature12373

# Reference search - author citation
./doi2bib.py --search "G. Thomas and M. J. Whelan, Phil. Mag. 4, 511 (1959)"

# Reference search - journal reference  
./doi2bib.py --search "PHYSICAL REVIEW MATERIALS 5, 083603 (2021)"

# Reference search - title only
./doi2bib.py --search "Kinetic Theory of Dislocation Climb"

# Download open access PDF (via Unpaywall)
./doi2bib.py --oa 10.1038/nature12373

# Open journal page (for institutional access)
./doi2bib.py --journal 10.1038/nature12373
./doi2bib.py -j 10.1038/nature12373
```

When searching, if multiple results are found, you'll be prompted to select one:
```
Found 5 results:
[0] G. Thomas, M. Whelan (1959) "Observations of precipitation..." Philosophical Magazine
[1] P. Hirsch, J. Whelan (1960) "Dislocation contrast..." Philosophical Magazine
...
Enter number to select (or 'q' to quit): 0
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

## Building from Source

If you want to build your own executables:

### macOS
```bash
chmod +x build_macos.sh
./build_macos.sh
# Output: dist/BibTexer.app
```

### Windows
```batch
build_windows.bat
# Output: dist\BibTexer.exe
```

### Linux
```bash
chmod +x build_linux.sh
./build_linux.sh
# Output: dist/BibTexer
```

## Supported Entry Types

BibTexer automatically detects and converts the following CrossRef types:

| CrossRef Type | BibTeX Type |
|---------------|-------------|
| journal-article | @article |
| proceedings-article | @inproceedings |
| book-chapter | @incollection |
| book, edited-book, monograph | @book |
| report | @techreport |
| dissertation | @phdthesis |
| dataset, posted-content | @misc |

## Get Paper Feature

BibTexer provides two ways to access papers:

### 📄 Open Access (via Unpaywall)
- Click **"📄 Open Access"** (GUI) or use `--oa` (CLI)
- Searches [Unpaywall](https://unpaywall.org/) for legal open access versions
- If found, downloads PDF to your **Downloads folder** and opens it
- Sources include: preprint servers (arXiv, bioRxiv), institutional repositories, publisher OA

### 🏛️ Journal (Institutional Access)
- Click **"🏛️ Journal"** (GUI) or use `--journal` (CLI)
- Opens the publisher's page via DOI URL
- Use your **institutional login** or campus network for access
- Works with any subscription your institution has

### CLI Examples

```bash
# Try to download open access version
./doi2bib.py --oa 10.1038/nature12373

# Open publisher page (for institutional access)
./doi2bib.py --journal 10.1038/nature12373
./doi2bib.py -j 10.1038/nature12373   # short form
```

### Privacy Note

The Unpaywall API query includes only the DOI - no personal information is transmitted.

## Clipboard Support

Clipboard functionality works automatically on:
- **macOS**: Uses `pbcopy` (built-in)
- **Windows**: Uses `clip` (built-in)
- **Linux**: Requires `xclip` or `xsel` (`sudo apt install xclip`)

## Project Structure

```
BibTexer/
├── bibtexer_core.py          # Core library (API, parsing, conversion)
├── bibtexer_gui.py           # GUI application (imports from core)
├── doi2bib.py                # Command-line tool (imports from core)
├── journal_abbreviations.json # Journal abbreviations database (400+ entries)
├── requirements.txt          # Python dependencies
├── build_macos.sh            # macOS build script
├── build_windows.bat         # Windows build script
├── build_linux.sh            # Linux build script
├── .github/
│   └── workflows/
│       └── build-release.yml # Automated release builds
├── LICENSE                   # AGPL-3.0 license
└── README.md                 # This file
```

The codebase follows a modular design where `bibtexer_core.py` contains all shared functionality (CrossRef API, reference parsing, BibTeX conversion), while the GUI and CLI are thin frontend layers.

## Journal Abbreviations

BibTexer includes a comprehensive database of **400+ journal abbreviations** covering multiple scientific disciplines:

- **Multidisciplinary**: Nature, Science, PNAS, etc.
- **Physics**: Physical Review family, Journal of Applied Physics, etc.
- **Materials Science**: Acta Materialia, Advanced Materials, etc.
- **Chemistry**: JACS, Angewandte Chemie, Inorganic Chemistry, etc.
- **Medicine**: NEJM, Lancet, JAMA, BMJ, etc.
- **Biology**: Cell, Neuron, Immunity, Plant Cell, etc.
- **Earth Science**: Geology, GRL, Nature Geoscience, etc.
- **Engineering**: IEEE Transactions, AIAA Journal, etc.
- **Computer Science**: ACM journals, JMLR, etc.
- **Mathematics**: Annals of Mathematics, SIAM journals, etc.

### Extending the Abbreviations

The abbreviations are stored in `journal_abbreviations.json`. To add custom abbreviations:

1. Open `journal_abbreviations.json` in a text editor
2. Add entries to the `"abbreviations"` section:
   ```json
   "your abbrev.": "Full Journal Name",
   ```
3. Restart BibTexer

Abbreviations are case-insensitive. Contributions to expand the database are welcome!

## Changelog

### Version 2.2.1
- **Get Paper feature**: Two options for paper access:
  - "📄 Open Access" - Download free PDFs via Unpaywall
  - "🏛️ Journal" - Open publisher page for institutional access
- Modular codebase: Shared logic in `bibtexer_core.py`
- External `journal_abbreviations.json` with 400+ entries across all disciplines
- CLI: Added `--oa` and `--journal` flags, plus `--version`/`--help` options
- Improved window sizing and button layout

### Version 2.1.0
- Added automated builds for all platforms via GitHub Actions
- Pre-built installers now available for Windows, macOS (Intel & Apple Silicon), and Linux
- No Python installation required for end users

### Version 2.0.0
- Added Reference Search feature - search by author, title, journal without DOI
- Intelligent citation parser extracts metadata from various formats
- Journal abbreviations database for better matching
- Multiple result selection dialog
- Tabbed GUI interface

### Version 1.0.0
- Initial release
- DOI to BibTeX conversion
- Cross-platform GUI
- Clipboard support
- Build scripts for all platforms

## Citation

If you use BibTexer in your research, please cite it as:

```bibtex
@software{bitzek2026bibtexer,
  author = {Bitzek, Erik},
  title = {BibTexer: DOI and Reference to BibTeX Converter},
  year = {2026},
  version = {2.2.1},
  url = {https://github.com/biterik/BibTexer},
  note = {Part of the MatWerk Scholar Toolbox, developed within NFDI-MatWerk}
}
```

## Acknowledgments

BibTexer is part of the **MatWerk Scholar Toolbox** and was developed within **NFDI-MatWerk** (National Research Data Infrastructure for Materials Science and Engineering).

[![NFDI-MatWerk](https://nfdi-matwerk.de/)](https://nfdi-matwerk.de/)

This work was funded by the German Research Foundation (DFG) through the NFDI-MatWerk consortium.

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Author

Erik Bitzek

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
