# BibTexer Project Checkpoint - January 24, 2026

## Current Version: 4.0.0

## Repository
- GitHub: https://github.com/biterik/BibTexer
- Local: `/Users/oq50iqeq/Desktop/PROJECTS/DEVEL/BIBTEXER`

## What's New in v4.0
- ✅ **RIS format output** (radio button selector in GUI, --ris flag in CLI)
- ✅ **Zotero local connector integration** (📚 Add to Zotero button, --zotero flag)
- ✅ **Export section** in GUI with Zotero status indicator
- ✅ Updated README with full documentation

## Working Features
- ✅ DOI lookup → BibTeX/RIS conversion
- ✅ Reference search (author, title, journal, year)
- ✅ Search results dialog (multiple matches)
- ✅ 📄 Open Access button (Unpaywall API)
- ✅ 🏛️ Journal button (DOI URL for institutional access)
- ✅ 📚 Add to Zotero button (local connector on port 23119)
- ✅ Format selector: BibTeX / RIS (radio buttons)
- ✅ Copy to clipboard
- ✅ Dark/Light mode
- ✅ 400+ journal abbreviations (external JSON)
- ✅ CLI with --ris, --zotero, --oa, --journal, --search flags

## Known Bug (from v3.0.1)
**macOS app (PyInstaller build) does not show the search results dialog window**
- Works correctly when running `python bibtexer_gui.py`
- Fails in the packaged `.app` from GitHub releases
- Dialog window (`SearchResultsDialog`) doesn't appear when multiple search results are found
- **Status**: Not yet fixed in v4.0

## Project Files

### Core Files
| File | Purpose |
|------|---------|
| `bibtexer_core.py` | Shared library (API, parsing, BibTeX/RIS conversion, Zotero) |
| `bibtexer_gui.py` | GUI application (CustomTkinter) |
| `doi2bib.py` | CLI tool |
| `journal_abbreviations.json` | 400+ journal abbreviations |
| `requirements.txt` | Python dependencies |

### Build Files
| File | Purpose |
|------|---------|
| `.github/workflows/build-release.yml` | GitHub Actions workflow |
| `build_macos.sh` | Local macOS build script |
| `build_windows.bat` | Local Windows build script |
| `build_linux.sh` | Local Linux build script |

## Architecture

```
bibtexer_core.py (v4.0.0)
├── CrossRef API functions
├── BibTeX conversion
├── RIS conversion (NEW)
├── CSL-JSON conversion (NEW, for Zotero)
├── Zotero local connector (NEW)
│   ├── is_zotero_running()
│   ├── send_to_zotero_local()
│   └── _send_to_zotero_via_import()
├── Reference parser
├── Journal abbreviations loader
├── Unpaywall API (paper download)
├── Clipboard functions
└── File/URL open functions

bibtexer_gui.py
├── BibTexerApp (main window)
│   ├── DOI Lookup tab
│   ├── Reference Search tab
│   ├── Output display with format selector (BibTeX/RIS)
│   ├── Buttons: Copy, Open Access, Journal, Clear
│   └── Export section: Add to Zotero + status indicator
└── SearchResultsDialog (modal) ← BUG: not showing in packaged app

doi2bib.py
├── --search mode
├── --ris mode (NEW)
├── --zotero mode (NEW)
├── --oa mode
├── --journal mode
└── DOI lookup mode
```

## New Functions in v4.0

### bibtexer_core.py
```python
# RIS conversion
get_ris_type(data: Dict) -> str
convert_to_ris(data: Dict) -> str

# Zotero integration
ZOTERO_CONNECTOR_PORT = 23119
is_zotero_running() -> bool
convert_to_csl_json(data: Dict) -> Dict
send_to_zotero_local(data: Dict) -> Tuple[bool, str]
_send_to_zotero_via_import(data: Dict) -> Tuple[bool, str]
```

## Dependencies
- Python 3.6+
- customtkinter >= 5.0.0
- pyinstaller >= 5.0.0 (for builds)

## Zotero Integration Details
- Uses local connector on `http://127.0.0.1:23119`
- Primary endpoint: `/connector/saveItems` (CSL-JSON)
- Fallback endpoint: `/connector/import` (RIS format)
- Zotero must be running for integration to work
- No API key required (uses same method as browser extensions)

## Commands to Run Locally

```bash
cd /Users/oq50iqeq/Desktop/PROJECTS/DEVEL/BIBTEXER

# Run from source (works)
python bibtexer_gui.py

# CLI examples
python doi2bib.py 10.1038/nature12373           # BibTeX
python doi2bib.py --ris 10.1038/nature12373     # RIS
python doi2bib.py --zotero 10.1038/nature12373  # Add to Zotero

# Build locally to test
./build_macos.sh

# Test local build
open dist/BibTexer.app
```

## Commands to Push Updates

```bash
git add .
git commit -m "v4.0.0: Add Zotero integration and RIS export"
git push origin main

# For new release:
git tag v4.0.0
git push origin v4.0.0
```

## TODO / Future Ideas
- [ ] Fix SearchResultsDialog in PyInstaller build
- [ ] Add Zotero collection selection (choose which collection to add to)
- [ ] Add BibLaTeX format option
- [ ] Add CSL-JSON export option
- [ ] Batch DOI processing
