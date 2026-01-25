# BibTexer v4.1.0 Checkpoint - January 25, 2026

## Project Overview
**BibTexer** - DOI/Reference to BibTeX converter with Zotero integration
Part of the MatWerk Scholar Toolbox - Developed within NFDI-MatWerk

**Repository**: https://github.com/biterik/BibTexer
**Version**: 4.1.0
**Author**: Erik Bitzek

## What's New in v4.1.0

### New Features (from v4.0.0)
- **RIS Format Export**: GUI radio buttons to select BibTeX or RIS output, CLI `--ris` flag
- **Zotero Integration**: Direct integration via local connector (port 23119), GUI button with status indicator, CLI `--zotero` flag
- **Reference Search as Default**: The app now opens to the Reference Search tab

### Bug Fixes in v4.1.0
- **SSL Certificate Handling**: Fixed `CERTIFICATE_VERIFY_FAILED` errors in PyInstaller bundles using certifi
- **Search Results Dialog**: New popup dialog with multi-line format (title, authors, journal/year/DOI)
- **Journal Abbreviation Matching**: Fixed word boundary matching (no longer matches "structure" inside "nanostructure")
- **Whitespace Normalization**: Handles line breaks in pasted references (e.g., "Nat\nCommun" → "Nature Communications")
- **Author Parsing**: Added support for "Ji B, Gao H" format (surname + initial without period)
- **Title Extraction**: Improved patterns for extracting titles from references like "(2023) Title here. Journal"

### UI Improvements
- Standard `tk.Text` widget for output (more reliable in bundled apps)
- Multi-line search results with proper formatting
- Horizontal and vertical scrollbars in search results dialog

## Architecture

```
bibtexer/
├── bibtexer_core.py      # Core library (v4.1.0)
│   ├── CrossRef API integration
│   ├── BibTeX/RIS conversion
│   ├── Reference parsing
│   ├── Zotero local connector
│   └── SSL certificate handling (certifi)
├── bibtexer_gui.py       # GUI application
│   ├── DOI Lookup tab
│   ├── Reference Search tab (default)
│   ├── Format selector (BibTeX/RIS)
│   ├── Zotero export button
│   └── SearchResultsDialog (multi-line format)
├── doi2bib.py            # CLI tool
│   ├── --ris flag
│   ├── --zotero flag
│   └── --search flag
├── journal_abbreviations.json
├── requirements.txt
├── build_macos.sh
└── .github/workflows/build-release.yml
```

## Key Functions

### bibtexer_core.py
```python
# Main functions
get_crossref_data(doi: str) -> Dict
search_crossref(query, author, title, journal, year, rows) -> List[Dict]
convert_to_bibtex(data: Dict) -> str
convert_to_ris(data: Dict) -> str
parse_reference(text: str) -> Dict

# Zotero integration
is_zotero_running() -> bool
send_to_zotero_local(data: Dict) -> Tuple[bool, str]

# SSL handling
ssl_context = ssl.create_default_context(cafile=certifi.where())
```

### CLI Usage
```bash
# DOI lookup
python doi2bib.py 10.1038/nature12373

# RIS format
python doi2bib.py --ris 10.1038/nature12373

# Add to Zotero
python doi2bib.py --zotero 10.1038/nature12373

# Reference search
python doi2bib.py --search "Ji B, Gao H (2004) Mechanical properties"

# Combined
python doi2bib.py --search "Thomas Whelan 1959" --ris --zotero
```

## Dependencies
```
customtkinter>=5.0.0
pyinstaller>=5.0.0
certifi
```

## Build Configuration

### GitHub Actions (.github/workflows/build-release.yml)
- Python 3.11 (for better tkinter compatibility)
- Pinned versions: customtkinter==5.2.2, pyinstaller==6.3.0
- Includes certifi for SSL certificates
- Builds for: macOS, Windows, Linux

### Local Build (macOS)
```bash
./build_macos.sh
```

## Testing Checklist

### DOI Lookup
- [ ] Enter DOI → Get BibTeX
- [ ] Switch to RIS format
- [ ] Copy to clipboard
- [ ] Add to Zotero (with Zotero running)

### Reference Search
- [ ] Paste reference with line breaks
- [ ] Authors parsed correctly
- [ ] Journal abbreviation matched
- [ ] Title extracted
- [ ] Multiple results → Dialog appears
- [ ] Select and confirm result

### Sample References for Testing
```
Ji B, Gao H (2004) Mechanical properties of nanostructure of biological materials. J Mech Phys Solids 52:1963–1990

Dong P, Xia K, Xu Y et al (2023) Laboratory earthquakes decipher control and stability of rupture speeds. Nat Commun 14:2427

G. Thomas and M. J. Whelan (1959) Phil. Mag. 4:511-527
```

## Known Issues
- None currently

## Files Modified Since v3.0.1
| File | Changes |
|------|---------|
| bibtexer_core.py | RIS export, Zotero integration, SSL handling, improved parsing |
| bibtexer_gui.py | Format selector, Zotero button, SearchResultsDialog, tk.Text output |
| doi2bib.py | --ris and --zotero flags |
| build-release.yml | Python 3.11, pinned versions, certifi |
| requirements.txt | Added certifi |

## Git Commands for Release

```bash
cd /Users/oq50iqeq/Desktop/PROJECTS/DEVEL/BIBTEXER

# Stage all changes
git add -A

# Commit
git commit -m "v4.1.0: Zotero integration, RIS export, improved parsing

New features:
- RIS format export (GUI + CLI)
- Direct Zotero integration via local connector
- Reference Search as default tab

Bug fixes:
- SSL certificates for bundled apps (certifi)
- Journal abbreviation word boundary matching
- Whitespace normalization in reference parsing
- Author parsing for 'Ji B, Gao H' format
- Title extraction improvements

Technical changes:
- Multi-line search results dialog
- tk.Text widget for reliable output display
- Python 3.11 + pinned package versions in CI"

# Push
git push origin main

# Delete test tags
git tag -d v4.0.0-rc1 v4.0.0-rc2 v4.0.0-rc3 v4.0.0-rc4 v4.0.0-rc5 v4.0.0-rc6 v4.0.0-rc7
git push origin --delete v4.0.0-rc1 v4.0.0-rc2 v4.0.0-rc3 v4.0.0-rc4 v4.0.0-rc5 v4.0.0-rc6 v4.0.0-rc7

# Create release tag
git tag -a v4.1.0 -m "Version 4.1.0: Zotero integration, RIS export, improved parsing"
git push origin v4.1.0
```

## Next Steps / Future Ideas
- Batch processing of multiple DOIs/references
- Export to other formats (EndNote, etc.)
- Local database of converted references
- Integration with other reference managers
