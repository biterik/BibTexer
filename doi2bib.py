#!/usr/bin/env python3
"""
BibTexer CLI - A command line tool to convert DOI or reference to BibTeX entry

Part of the MatWerk Scholar Toolbox - Developed within NFDI-MatWerk (https://nfdi-matwerk.de/)
Copyright (c) 2026 Erik Bitzek

Usage: 
  doi2bib.py <doi>                    # Lookup by DOI (BibTeX output)
  doi2bib.py --ris <doi>              # Lookup by DOI (RIS output)
  doi2bib.py --search "<reference>"   # Search by reference text
  doi2bib.py --zotero <doi>           # Add directly to Zotero

Examples: 
  doi2bib.py 10.1038/nature12373
  doi2bib.py --ris 10.1038/nature12373
  doi2bib.py --zotero 10.1038/nature12373
  doi2bib.py --search "G. Thomas and M. J. Whelan, Phil. Mag. 4, 511 (1959)"
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
    convert_to_ris,
    parse_reference,
    format_search_result_short,
    copy_to_clipboard,
    download_or_open_paper,
    open_url,
    get_doi_url,
    is_zotero_running,
    send_to_zotero_local,
)


def print_usage():
    """Print usage information."""
    print(f"BibTexer CLI v{__version__} - Convert DOI or reference to BibTeX/RIS", file=sys.stderr)
    print(f"Part of the {__project__}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Usage:", file=sys.stderr)
    print("  doi2bib.py <doi>                    # Lookup by DOI (BibTeX output)", file=sys.stderr)
    print('  doi2bib.py --search "<reference>"   # Search by reference text', file=sys.stderr)
    print("  doi2bib.py --ris <doi>              # Output in RIS format", file=sys.stderr)
    print("  doi2bib.py --zotero <doi>           # Add directly to local Zotero", file=sys.stderr)
    print("  doi2bib.py --oa <doi>               # Download open access PDF (via Unpaywall)", file=sys.stderr)
    print("  doi2bib.py --journal <doi>          # Open journal page (institutional access)", file=sys.stderr)
    print("", file=sys.stderr)
    print("Options:", file=sys.stderr)
    print("  --ris            Output in RIS format (for Zotero, Mendeley, EndNote, etc.)", file=sys.stderr)
    print("  --zotero, -z     Send reference directly to local Zotero (must be running)", file=sys.stderr)
    print("  --oa             Download open access PDF via Unpaywall", file=sys.stderr)
    print("  --journal, -j    Open publisher page (use institutional access)", file=sys.stderr)
    print("  --search, -s     Search by reference text instead of DOI", file=sys.stderr)
    print("  --version, -v    Show version information", file=sys.stderr)
    print("  --help, -h       Show this help message", file=sys.stderr)
    print("", file=sys.stderr)
    print("Examples:", file=sys.stderr)
    print("  doi2bib.py 10.1038/nature12373", file=sys.stderr)
    print("  doi2bib.py --ris 10.1038/nature12373        # RIS format output", file=sys.stderr)
    print("  doi2bib.py --zotero 10.1038/nature12373     # Add to Zotero", file=sys.stderr)
    print("  doi2bib.py --oa 10.1038/nature12373         # Download OA version", file=sys.stderr)
    print("  doi2bib.py --journal 10.1038/nature12373    # Open Nature website", file=sys.stderr)
    print('  doi2bib.py --search "G. Thomas and M. J. Whelan, Phil. Mag. 4, 511 (1959)"', file=sys.stderr)
    print('  doi2bib.py --search "Thomas Whelan" --ris   # Search + RIS output', file=sys.stderr)


def handle_search(search_text: str, output_ris: bool = False):
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
        
        selected_data = None
        
        if len(results) == 1:
            # Single result, use directly
            selected_data = results[0]
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
                    selected_data = results[idx]
                else:
                    print("Invalid selection.", file=sys.stderr)
                    sys.exit(1)
            except (ValueError, EOFError):
                print("Invalid input.", file=sys.stderr)
                sys.exit(1)
        
        if selected_data:
            if output_ris:
                output = convert_to_ris(selected_data)
                format_name = "RIS"
            else:
                output = convert_to_bibtex(selected_data)
                format_name = "BibTeX"
            
            print(output)
            if copy_to_clipboard(output):
                print(f"\n✓ {format_name} copied to clipboard!", file=sys.stderr)
            
            return selected_data
                
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_doi(doi: str, output_ris: bool = False):
    """Handle DOI lookup mode."""
    doi = clean_doi(doi)
    
    try:
        data = get_crossref_data(doi)
        
        if output_ris:
            output = convert_to_ris(data)
            format_name = "RIS"
        else:
            output = convert_to_bibtex(data)
            format_name = "BibTeX"
        
        print(output)
        
        if copy_to_clipboard(output):
            print(f"\n✓ {format_name} copied to clipboard!", file=sys.stderr)
        else:
            print("\n⚠ Could not copy to clipboard", file=sys.stderr)
        
        return data
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_zotero(doi: str):
    """Handle adding reference to local Zotero."""
    doi = clean_doi(doi)
    
    # Check if Zotero is running
    if not is_zotero_running():
        print("Error: Zotero is not running.", file=sys.stderr)
        print("Please open Zotero and try again.", file=sys.stderr)
        sys.exit(1)
    
    print("Fetching reference data...", file=sys.stderr)
    
    try:
        data = get_crossref_data(doi)
        
        print("Sending to Zotero...", file=sys.stderr)
        success, message = send_to_zotero_local(data)
        
        if success:
            print(f"✓ {message}", file=sys.stderr)
            
            # Also output BibTeX for reference
            bibtex = convert_to_bibtex(data)
            print("\nBibTeX entry:")
            print(bibtex)
        else:
            print(f"⚠ {message}", file=sys.stderr)
            sys.exit(1)
            
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_oa(doi: str):
    """Handle open access download mode (via Unpaywall)."""
    doi = clean_doi(doi)
    
    print("Searching Unpaywall for open access version...", file=sys.stderr)
    
    try:
        result = download_or_open_paper(
            doi,
            open_pdf=True,
            fallback_browser=False  # Don't fall back to DOI URL
        )
        
        if result['success']:
            print(f"✓ {result['message']}", file=sys.stderr)
        elif result.get('pdf_url'):
            # Found URL but couldn't download directly - open it
            print(f"Found open access version, opening in browser...", file=sys.stderr)
            if open_url(result['pdf_url']):
                print(f"📄 Opened: {result['pdf_url']}", file=sys.stderr)
            else:
                print(f"Open access URL: {result['pdf_url']}", file=sys.stderr)
        else:
            print("No open access version found.", file=sys.stderr)
            print(f"Try: doi2bib.py --journal {doi}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_journal(doi: str):
    """Handle journal page opening (for institutional access)."""
    doi = clean_doi(doi)
    doi_url = get_doi_url(doi)
    
    print(f"Opening journal page: {doi_url}", file=sys.stderr)
    
    if open_url(doi_url):
        print("🏛️ Opened in browser - use institutional login if needed", file=sys.stderr)
    else:
        print(f"Could not open browser.", file=sys.stderr)
        print(f"URL: {doi_url}", file=sys.stderr)
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
    
    # Parse arguments to check for --ris flag anywhere
    output_ris = '--ris' in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != '--ris']
    
    if not args:
        print_usage()
        sys.exit(1)
    
    # Check for search mode
    if args[0] in ['--search', '-s']:
        if len(args) < 2:
            print("Error: --search requires a reference string", file=sys.stderr)
            print_usage()
            sys.exit(1)
        search_text = ' '.join(args[1:])
        handle_search(search_text, output_ris=output_ris)
    
    # Check for Zotero mode
    elif args[0] in ['--zotero', '-z']:
        if len(args) < 2:
            print("Error: --zotero requires a DOI", file=sys.stderr)
            print_usage()
            sys.exit(1)
        handle_zotero(args[1])
    
    # Check for open access download mode
    elif args[0] == '--oa':
        if len(args) < 2:
            print("Error: --oa requires a DOI", file=sys.stderr)
            print_usage()
            sys.exit(1)
        handle_oa(args[1])
    
    # Check for journal page mode
    elif args[0] in ['--journal', '-j']:
        if len(args) < 2:
            print("Error: --journal requires a DOI", file=sys.stderr)
            print_usage()
            sys.exit(1)
        handle_journal(args[1])
    
    # Legacy --open support (maps to --oa for backwards compatibility)
    elif args[0] in ['--open', '-o']:
        if len(args) < 2:
            print("Error: --open requires a DOI", file=sys.stderr)
            print_usage()
            sys.exit(1)
        print("Note: --open is deprecated, use --oa or --journal", file=sys.stderr)
        handle_oa(args[1])
    
    # RIS-only mode (--ris as first argument)
    elif args[0] == '--ris':
        # --ris was already filtered out, so this shouldn't happen
        # but handle the case where --ris is the only argument
        print("Error: --ris requires a DOI", file=sys.stderr)
        print_usage()
        sys.exit(1)
    
    else:
        # DOI mode
        handle_doi(args[0], output_ris=output_ris)


if __name__ == "__main__":
    main()
