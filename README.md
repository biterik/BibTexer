# BibTexer

A command line tool that converts DOIs to complete BibTeX entries using the CrossRef API.

## Features

- Fetches publication metadata from CrossRef API
- Generates properly formatted BibTeX entries
- Automatically determines entry type (article, inproceedings, book, etc.)
- Creates citation keys from first author's name and publication year
- Escapes special LaTeX characters
- Copies result directly to clipboard (macOS)
- Accepts DOIs in various formats (plain, `doi:` prefix, or full URL)

## Requirements

- Python 3.6+
- macOS (for clipboard support via `pbcopy`)

## Installation

```bash
git clone https://github.com/biterik/BibTexer.git
cd BibTexer
chmod +x doi2bib.py
```

## Usage

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

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Author

Erik Bitzek
