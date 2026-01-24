#!/usr/bin/env python3
"""
BibTexer CLI - A command line tool to convert DOI or reference to BibTeX entry

Part of the MatWerk Scholar Toolbox - Developed within NFDI-MatWerk (https://nfdi-matwerk.de/)
Copyright (c) 2026 Erik Bitzek

Usage: 
  doi2bib.py <doi>                    # Lookup by DOI
  doi2bib.py --search "<reference>"   # Search by reference text

Examples: 
  doi2bib.py 10.1038/nature12373
  doi2bib.py --search "G. Thomas and M. J. Whelan, Phil. Mag. 4, 511 (1959)"
  doi2bib.py --search "PHYSICAL REVIEW MATERIALS 5, 083603 (2021)"
"""

import sys

from bibtexer_core import (
    __version__,
    __author__,
    __project__,
    clean_doi,
    get_crossref_data,
    search_crossref,
    convert_to_bibtex,
    parse_reference,
    format_search_result_short,
    copy_to_clipboard,
)


def print_usage():
    """Print usage information."""
    print(f"BibTexer CLI v{__version__} - Convert DOI or reference to BibTeX", file=sys.stderr)
    print(f"Part of the {__project__}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Usage:", file=sys.stderr)
    print("  doi2bib.py <doi>                    # Lookup by DOI", file=sys.stderr)
    print('  doi2bib.py --search "<reference>"   # Search by reference text', file=sys.stderr)
    print("", file=sys.stderr)
    print("Examples:", file=sys.stderr)
    print("  doi2bib.py 10.1038/nature12373", file=sys.stderr)
    print('  doi2bib.py --search "G. Thomas and M. J. Whelan, Phil. Mag. 4, 511 (1959)"', file=sys.stderr)
    print('  doi2bib.py --search "PHYSICAL REVIEW MATERIALS 5, 083603 (2021)"', file=sys.stderr)


def handle_search(search_text: str):
    """Handle reference search mode."""
    try:
        parsed = parse_reference(search_text)
        
        # Show parsed info
        print("Searching CrossRef...", file=sys.stderr)
        parsed_parts = []
        if parsed['authors']:
            parsed_parts.append(f"Authors: {parsed['authors']}")
        if parsed['year']:
            parsed_parts.append(f"Year: {parsed['year']}")
        if parsed['journal']:
            parsed_parts.append(f"Journal: {parsed['journal']}")
        if parsed['title']:
            parsed_parts.append(f"Title: {parsed['title'][:40]}...")
        if parsed_parts:
            print(f"Parsed: {' | '.join(parsed_parts)}", file=sys.stderr)
        
        results = search_crossref(
            query=parsed['query'] if not parsed['title'] and not parsed['authors'] else None,
            author=parsed['authors'],
            title=parsed['title'],
            journal=parsed['journal'],
            year=parsed['year'],
            rows=10
        )
        
        if not results:
            print("No results found.", file=sys.stderr)
            sys.exit(1)
        
        if len(results) == 1:
            # Single result, use directly
            bibtex = convert_to_bibtex(results[0])
            print(bibtex)
            if copy_to_clipboard(bibtex):
                print("\n✓ Copied to clipboard!", file=sys.stderr)
        else:
            # Multiple results, show selection
            print(f"\nFound {len(results)} results:", file=sys.stderr)
            for i, item in enumerate(results):
                print(format_search_result_short(item, i), file=sys.stderr)
            
            print("\nEnter number to select (or 'q' to quit): ", file=sys.stderr, end='')
            try:
                choice = input().strip()
                if choice.lower() == 'q':
                    sys.exit(0)
                idx = int(choice)
                if 0 <= idx < len(results):
                    bibtex = convert_to_bibtex(results[idx])
                    print(bibtex)
                    if copy_to_clipboard(bibtex):
                        print("\n✓ Copied to clipboard!", file=sys.stderr)
                else:
                    print("Invalid selection.", file=sys.stderr)
                    sys.exit(1)
            except (ValueError, EOFError):
                print("Invalid input.", file=sys.stderr)
                sys.exit(1)
                
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_doi(doi: str):
    """Handle DOI lookup mode."""
    doi = clean_doi(doi)
    
    try:
        data = get_crossref_data(doi)
        bibtex = convert_to_bibtex(data)
        print(bibtex)
        
        if copy_to_clipboard(bibtex):
            print("\n✓ Copied to clipboard!", file=sys.stderr)
        else:
            print("\n⚠ Could not copy to clipboard", file=sys.stderr)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    # Check for version flag
    if sys.argv[1] in ['--version', '-v']:
        print(f"BibTexer v{__version__}")
        print(f"Author: {__author__}")
        print(f"Project: {__project__}")
        sys.exit(0)
    
    # Check for help flag
    if sys.argv[1] in ['--help', '-h']:
        print_usage()
        sys.exit(0)
    
    # Check for search mode
    if sys.argv[1] in ['--search', '-s']:
        if len(sys.argv) < 3:
            print("Error: --search requires a reference string", file=sys.stderr)
            print_usage()
            sys.exit(1)
        search_text = ' '.join(sys.argv[2:])
        handle_search(search_text)
    else:
        # DOI mode
        handle_doi(sys.argv[1])


if __name__ == "__main__":
    main()
