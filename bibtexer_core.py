#!/usr/bin/env python3
"""
BibTexer Core - Shared functionality for DOI/reference to BibTeX conversion

Part of the MatWerk Scholar Toolbox - Developed within NFDI-MatWerk (https://nfdi-matwerk.de/)
Copyright (c) 2026 Erik Bitzek
"""

__version__ = "4.0.0"
__author__ = "Erik Bitzek"
__project__ = "MatWerk Scholar Toolbox"

import sys
import subprocess
import platform
import urllib.request
import urllib.parse
import urllib.error
import json
import re
import unicodedata
import socket
import ssl
import certifi
from typing import Optional, Dict, List, Tuple

# Fix SSL certificates for PyInstaller bundles
ssl_context = ssl.create_default_context(cafile=certifi.where())


# ============== Journal Abbreviations Database ==============

import os

def _load_journal_abbreviations() -> dict:
    """
    Load journal abbreviations from external JSON file.
    Falls back to minimal embedded list if file not found.
    """
    # Try multiple locations for the JSON file
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'journal_abbreviations.json'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'journal_abbreviations.json'),
        'journal_abbreviations.json',
        # For PyInstaller bundles
        os.path.join(getattr(sys, '_MEIPASS', ''), 'journal_abbreviations.json'),
    ]
    
    for path in possible_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                abbrevs = data.get('abbreviations', {})
                # Filter out comment entries (keys starting with _)
                return {k: v for k, v in abbrevs.items() if not k.startswith('_')}
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            continue
    
    # Fallback to minimal embedded list if file not found
    return {
        'nature': 'Nature',
        'science': 'Science',
        'pnas': 'Proceedings of the National Academy of Sciences',
        'phys. rev.': 'Physical Review',
        'phys. rev. lett.': 'Physical Review Letters',
        'j. am. chem. soc.': 'Journal of the American Chemical Society',
        'n. engl. j. med.': 'New England Journal of Medicine',
        'lancet': 'The Lancet',
        'cell': 'Cell',
        'proc. natl. acad. sci.': 'Proceedings of the National Academy of Sciences',
        'j mech phys solids': 'Journal of the Mechanics and Physics of Solids',
        'j. mech. phys. solids': 'Journal of the Mechanics and Physics of Solids',
    }


# Load abbreviations at module import time
JOURNAL_ABBREVIATIONS = _load_journal_abbreviations()


# ============== Text Processing ==============

def normalize_text(text: str) -> str:
    """Normalize unicode text and escape special LaTeX characters."""
    if not text:
        return ""
    text = unicodedata.normalize('NFC', text)
    special_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    for char, replacement in special_chars.items():
        text = text.replace(char, replacement)
    return text


def clean_doi(doi: str) -> str:
    """Clean and normalize a DOI string."""
    doi = doi.strip()
    doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
    doi = re.sub(r'^doi:', '', doi, flags=re.IGNORECASE)
    return doi


# ============== CrossRef API ==============

def get_crossref_data(doi: str) -> Dict:
    """Fetch metadata from CrossRef API for a given DOI."""
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', f'BibTexer/{__version__} (mailto:user@example.com)')
    req.add_header('Accept', 'application/json')
    
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data['message']
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"DOI not found: {doi}")
        else:
            raise ValueError(f"HTTP error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise ValueError(f"Network error: {e.reason}")
    except json.JSONDecodeError:
        raise ValueError("Invalid response from CrossRef API")


def search_crossref(
    query: Optional[str] = None,
    author: Optional[str] = None,
    title: Optional[str] = None,
    journal: Optional[str] = None,
    year: Optional[str] = None,
    rows: int = 10
) -> List[Dict]:
    """
    Search CrossRef API for references matching the given criteria.
    
    Returns a list of matching items with their metadata.
    """
    base_url = "https://api.crossref.org/works"
    params = {'rows': str(rows)}
    
    query_parts = []
    if query:
        query_parts.append(query)
    if title:
        query_parts.append(title)
    if author:
        params['query.author'] = author
    if journal:
        params['query.container-title'] = journal
    
    if query_parts:
        params['query'] = ' '.join(query_parts)
    
    filters = []
    if year:
        filters.append(f'from-pub-date:{year}')
        filters.append(f'until-pub-date:{year}')
    if filters:
        params['filter'] = ','.join(filters)
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', f'BibTexer/{__version__} (mailto:user@example.com)')
    req.add_header('Accept', 'application/json')
    
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data['message'].get('items', [])
    except Exception as e:
        raise ValueError(f"Search failed: {e}")


# ============== BibTeX Conversion ==============

def format_authors(authors: List[Dict]) -> Optional[str]:
    """Format author list for BibTeX."""
    if not authors:
        return None
    
    formatted = []
    for author in authors:
        family = author.get('family', '')
        given = author.get('given', '')
        if family and given:
            formatted.append(f"{family}, {given}")
        elif family:
            formatted.append(family)
        elif given:
            formatted.append(given)
    
    return " and ".join(formatted) if formatted else None


def generate_cite_key(data: Dict) -> str:
    """Generate a citation key from author and year."""
    authors = data.get('author', [])
    if authors and 'family' in authors[0]:
        author_part = authors[0]['family'].lower()
        author_part = re.sub(r'[^a-z]', '', author_part)
    else:
        author_part = 'unknown'
    
    date_parts = None
    for date_field in ['published-print', 'published-online', 'issued', 'created']:
        if date_field in data and 'date-parts' in data[date_field]:
            date_parts = data[date_field]['date-parts']
            break
    
    if date_parts and date_parts[0] and date_parts[0][0]:
        year_part = str(date_parts[0][0])
    else:
        year_part = 'nd'
    
    return f"{author_part}{year_part}"


def get_year(data: Dict) -> Optional[str]:
    """Extract publication year from data."""
    for date_field in ['published-print', 'published-online', 'issued', 'created']:
        if date_field in data and 'date-parts' in data[date_field]:
            date_parts = data[date_field]['date-parts']
            if date_parts and date_parts[0] and date_parts[0][0]:
                return str(date_parts[0][0])
    return None


def get_month(data: Dict) -> Optional[str]:
    """Extract publication month from data."""
    for date_field in ['published-print', 'published-online', 'issued']:
        if date_field in data and 'date-parts' in data[date_field]:
            date_parts = data[date_field]['date-parts']
            if date_parts and date_parts[0] and len(date_parts[0]) > 1:
                month_num = date_parts[0][1]
                months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                         'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                if 1 <= month_num <= 12:
                    return months[month_num - 1]
    return None


def get_entry_type(data: Dict) -> str:
    """Determine BibTeX entry type from CrossRef type."""
    crossref_type = data.get('type', 'journal-article')
    
    type_mapping = {
        'journal-article': 'article',
        'proceedings-article': 'inproceedings',
        'book-chapter': 'incollection',
        'book': 'book',
        'edited-book': 'book',
        'monograph': 'book',
        'report': 'techreport',
        'dissertation': 'phdthesis',
        'dataset': 'misc',
        'posted-content': 'misc',
        'reference-entry': 'misc',
    }
    
    return type_mapping.get(crossref_type, 'article')


def convert_to_bibtex(data: Dict) -> str:
    """Convert CrossRef metadata to BibTeX entry."""
    entry_type = get_entry_type(data)
    cite_key = generate_cite_key(data)
    
    fields = {}
    
    # Title
    if 'title' in data and data['title']:
        title = data['title'][0] if isinstance(data['title'], list) else data['title']
        fields['title'] = f"{{{normalize_text(title)}}}"
    
    # Authors
    authors = format_authors(data.get('author', []))
    if authors:
        fields['author'] = f"{{{normalize_text(authors)}}}"
    
    # Editors
    editors = format_authors(data.get('editor', []))
    if editors:
        fields['editor'] = f"{{{normalize_text(editors)}}}"
    
    # Year and Month
    year = get_year(data)
    if year:
        fields['year'] = f"{{{year}}}"
    
    month = get_month(data)
    if month:
        fields['month'] = month
    
    # Journal/Container
    if 'container-title' in data and data['container-title']:
        container = data['container-title'][0] if isinstance(data['container-title'], list) else data['container-title']
        if entry_type == 'article':
            fields['journal'] = f"{{{normalize_text(container)}}}"
        elif entry_type in ['incollection', 'inproceedings']:
            fields['booktitle'] = f"{{{normalize_text(container)}}}"
    
    # Volume
    if 'volume' in data and data['volume']:
        fields['volume'] = f"{{{data['volume']}}}"
    
    # Number/Issue
    if 'issue' in data and data['issue']:
        fields['number'] = f"{{{data['issue']}}}"
    
    # Pages
    if 'page' in data and data['page']:
        pages = data['page'].replace('-', '--')
        fields['pages'] = f"{{{pages}}}"
    
    # DOI
    if 'DOI' in data:
        fields['doi'] = f"{{{data['DOI']}}}"
    
    # URL
    if 'URL' in data:
        fields['url'] = f"{{{data['URL']}}}"
    
    # Publisher
    if 'publisher' in data and data['publisher']:
        fields['publisher'] = f"{{{normalize_text(data['publisher'])}}}"
    
    # ISSN
    if 'ISSN' in data and data['ISSN']:
        issn = data['ISSN'][0] if isinstance(data['ISSN'], list) else data['ISSN']
        fields['issn'] = f"{{{issn}}}"
    
    # ISBN
    if 'ISBN' in data and data['ISBN']:
        isbn = data['ISBN'][0] if isinstance(data['ISBN'], list) else data['ISBN']
        fields['isbn'] = f"{{{isbn}}}"
    
    # Abstract
    if 'abstract' in data and data['abstract']:
        abstract = re.sub(r'<[^>]+>', '', data['abstract'])
        fields['abstract'] = f"{{{normalize_text(abstract)}}}"
    
    # Build BibTeX string
    bibtex = f"@{entry_type}{{{cite_key},\n"
    
    field_order = ['author', 'title', 'journal', 'booktitle', 'year', 'month',
                   'volume', 'number', 'pages', 'publisher', 'editor',
                   'doi', 'url', 'issn', 'isbn', 'abstract']
    
    ordered_fields = []
    for field in field_order:
        if field in fields:
            ordered_fields.append((field, fields[field]))
    
    for field, value in fields.items():
        if field not in field_order:
            ordered_fields.append((field, value))
    
    for i, (field, value) in enumerate(ordered_fields):
        comma = "," if i < len(ordered_fields) - 1 else ""
        bibtex += f"  {field} = {value}{comma}\n"
    
    bibtex += "}"
    
    return bibtex


# ============== RIS Conversion (NEW in v4.0) ==============

def get_ris_type(data: Dict) -> str:
    """Determine RIS type from CrossRef type."""
    crossref_type = data.get('type', 'journal-article')
    
    type_mapping = {
        'journal-article': 'JOUR',
        'proceedings-article': 'CONF',
        'book-chapter': 'CHAP',
        'book': 'BOOK',
        'edited-book': 'EDBOOK',
        'monograph': 'BOOK',
        'report': 'RPRT',
        'dissertation': 'THES',
        'dataset': 'DATA',
        'posted-content': 'GEN',
        'reference-entry': 'GEN',
    }
    
    return type_mapping.get(crossref_type, 'JOUR')


def convert_to_ris(data: Dict) -> str:
    """
    Convert CrossRef metadata to RIS format.
    
    RIS is a standardized tag format for bibliographic data.
    Widely supported by Zotero, EndNote, Mendeley, Papers, etc.
    """
    lines = []
    
    # Type of reference
    lines.append(f"TY  - {get_ris_type(data)}")
    
    # Title
    if 'title' in data and data['title']:
        title = data['title'][0] if isinstance(data['title'], list) else data['title']
        # Remove any HTML tags
        title = re.sub(r'<[^>]+>', '', title)
        lines.append(f"TI  - {title}")
    
    # Authors (each author on separate AU line)
    if 'author' in data:
        for author in data['author']:
            family = author.get('family', '')
            given = author.get('given', '')
            if family and given:
                lines.append(f"AU  - {family}, {given}")
            elif family:
                lines.append(f"AU  - {family}")
            elif given:
                lines.append(f"AU  - {given}")
    
    # Editors
    if 'editor' in data:
        for editor in data['editor']:
            family = editor.get('family', '')
            given = editor.get('given', '')
            if family and given:
                lines.append(f"ED  - {family}, {given}")
            elif family:
                lines.append(f"ED  - {family}")
    
    # Publication year
    year = get_year(data)
    if year:
        lines.append(f"PY  - {year}")
    
    # Full date if available
    for date_field in ['published-print', 'published-online', 'issued']:
        if date_field in data and 'date-parts' in data[date_field]:
            date_parts = data[date_field]['date-parts']
            if date_parts and date_parts[0]:
                parts = date_parts[0]
                if len(parts) >= 3:
                    lines.append(f"DA  - {parts[0]}/{parts[1]:02d}/{parts[2]:02d}")
                elif len(parts) >= 2:
                    lines.append(f"DA  - {parts[0]}/{parts[1]:02d}")
                break
    
    # Journal/Container title
    if 'container-title' in data and data['container-title']:
        container = data['container-title'][0] if isinstance(data['container-title'], list) else data['container-title']
        if get_ris_type(data) == 'JOUR':
            lines.append(f"JO  - {container}")
            # Also add abbreviated journal title if different
            lines.append(f"T2  - {container}")
        else:
            lines.append(f"T2  - {container}")
    
    # Volume
    if 'volume' in data and data['volume']:
        lines.append(f"VL  - {data['volume']}")
    
    # Issue
    if 'issue' in data and data['issue']:
        lines.append(f"IS  - {data['issue']}")
    
    # Pages
    if 'page' in data and data['page']:
        pages = data['page']
        if '-' in pages:
            parts = re.split(r'[-–—]', pages)
            if len(parts) >= 2:
                lines.append(f"SP  - {parts[0].strip()}")
                lines.append(f"EP  - {parts[1].strip()}")
        else:
            lines.append(f"SP  - {pages}")
    
    # DOI
    if 'DOI' in data:
        lines.append(f"DO  - {data['DOI']}")
    
    # URL
    if 'URL' in data:
        lines.append(f"UR  - {data['URL']}")
    
    # Publisher
    if 'publisher' in data and data['publisher']:
        lines.append(f"PB  - {data['publisher']}")
    
    # ISSN
    if 'ISSN' in data and data['ISSN']:
        issn = data['ISSN'][0] if isinstance(data['ISSN'], list) else data['ISSN']
        lines.append(f"SN  - {issn}")
    
    # ISBN
    if 'ISBN' in data and data['ISBN']:
        isbn = data['ISBN'][0] if isinstance(data['ISBN'], list) else data['ISBN']
        lines.append(f"SN  - {isbn}")
    
    # Abstract
    if 'abstract' in data and data['abstract']:
        abstract = re.sub(r'<[^>]+>', '', data['abstract'])
        lines.append(f"AB  - {abstract}")
    
    # Language
    if 'language' in data and data['language']:
        lines.append(f"LA  - {data['language']}")
    
    # Keywords/subjects
    if 'subject' in data and data['subject']:
        for subject in data['subject']:
            lines.append(f"KW  - {subject}")
    
    # End of record
    lines.append("ER  - ")
    
    return '\n'.join(lines)


# ============== Zotero Integration (NEW in v4.0) ==============

ZOTERO_CONNECTOR_PORT = 23119
ZOTERO_CONNECTOR_URL = f"http://127.0.0.1:{ZOTERO_CONNECTOR_PORT}"


def is_zotero_running() -> bool:
    """
    Check if Zotero is running by testing the local connector port.
    
    Zotero runs a local web server on port 23119 for browser connector integration.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', ZOTERO_CONNECTOR_PORT))
        sock.close()
        return result == 0
    except Exception:
        return False


def convert_to_csl_json(data: Dict) -> Dict:
    """
    Convert CrossRef metadata to CSL-JSON format.
    
    CSL-JSON is the format used by Zotero and other citation managers.
    CrossRef data is already close to CSL-JSON, but needs some adjustments.
    """
    csl = {}
    
    # Type mapping
    crossref_type = data.get('type', 'journal-article')
    type_mapping = {
        'journal-article': 'article-journal',
        'proceedings-article': 'paper-conference',
        'book-chapter': 'chapter',
        'book': 'book',
        'edited-book': 'book',
        'monograph': 'book',
        'report': 'report',
        'dissertation': 'thesis',
        'dataset': 'dataset',
        'posted-content': 'article',
        'reference-entry': 'entry',
    }
    csl['type'] = type_mapping.get(crossref_type, 'article-journal')
    
    # Title
    if 'title' in data and data['title']:
        title = data['title'][0] if isinstance(data['title'], list) else data['title']
        csl['title'] = re.sub(r'<[^>]+>', '', title)
    
    # Authors
    if 'author' in data:
        csl['author'] = []
        for author in data['author']:
            author_obj = {}
            if 'family' in author:
                author_obj['family'] = author['family']
            if 'given' in author:
                author_obj['given'] = author['given']
            if author_obj:
                csl['author'].append(author_obj)
    
    # Editors
    if 'editor' in data:
        csl['editor'] = []
        for editor in data['editor']:
            editor_obj = {}
            if 'family' in editor:
                editor_obj['family'] = editor['family']
            if 'given' in editor:
                editor_obj['given'] = editor['given']
            if editor_obj:
                csl['editor'].append(editor_obj)
    
    # Date
    for date_field in ['published-print', 'published-online', 'issued', 'created']:
        if date_field in data and 'date-parts' in data[date_field]:
            date_parts = data[date_field]['date-parts']
            if date_parts and date_parts[0]:
                csl['issued'] = {'date-parts': date_parts}
                break
    
    # Container/Journal title
    if 'container-title' in data and data['container-title']:
        container = data['container-title'][0] if isinstance(data['container-title'], list) else data['container-title']
        csl['container-title'] = container
    
    # Volume, issue, page
    if 'volume' in data:
        csl['volume'] = data['volume']
    if 'issue' in data:
        csl['issue'] = data['issue']
    if 'page' in data:
        csl['page'] = data['page']
    
    # DOI and URL
    if 'DOI' in data:
        csl['DOI'] = data['DOI']
    if 'URL' in data:
        csl['URL'] = data['URL']
    
    # Publisher
    if 'publisher' in data:
        csl['publisher'] = data['publisher']
    
    # ISSN
    if 'ISSN' in data and data['ISSN']:
        issn = data['ISSN'][0] if isinstance(data['ISSN'], list) else data['ISSN']
        csl['ISSN'] = issn
    
    # ISBN
    if 'ISBN' in data and data['ISBN']:
        isbn = data['ISBN'][0] if isinstance(data['ISBN'], list) else data['ISBN']
        csl['ISBN'] = isbn
    
    # Abstract
    if 'abstract' in data and data['abstract']:
        csl['abstract'] = re.sub(r'<[^>]+>', '', data['abstract'])
    
    # Language
    if 'language' in data:
        csl['language'] = data['language']
    
    return csl


def send_to_zotero_local(data: Dict) -> Tuple[bool, str]:
    """
    Send a reference to local Zotero via the connector API.
    
    Uses the import endpoint with BibTeX format, which is most reliable.
    Zotero must be running for this to work.
    
    Args:
        data: CrossRef metadata dict
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    import time
    
    if not is_zotero_running():
        return False, "Zotero is not running. Please open Zotero and try again."
    
    # Convert to BibTeX - Zotero handles this format very reliably
    bibtex_data = convert_to_bibtex(data)
    
    url = f"{ZOTERO_CONNECTOR_URL}/connector/import"
    
    # Try up to 3 times with small delays (409 = Zotero busy)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                data=bibtex_data.encode('utf-8'),
                headers={
                    'Content-Type': 'application/x-bibtex',
                    'User-Agent': f'BibTexer/{__version__}'
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                if response.status in [200, 201]:
                    return True, "Reference added to Zotero!"
                else:
                    return False, f"Import failed: {response.status}"
                    
        except urllib.error.HTTPError as e:
            if e.code == 409 and attempt < max_retries - 1:
                # Zotero is busy, wait and retry
                time.sleep(0.5)
                continue
            elif e.code == 409:
                return False, "Zotero is busy. Please wait a moment and try again."
            else:
                return False, f"Zotero error: {e.code} - {e.reason}"
        except urllib.error.URLError as e:
            return False, f"Connection error: {e.reason}"
        except Exception as e:
            return False, f"Import error: {str(e)}"
    
    return False, "Could not connect to Zotero after multiple attempts."


# ============== Reference Parser ==============

def parse_reference(text: str) -> Dict[str, Optional[str]]:
    """
    Parse a reference string and extract components like authors, year, title, journal, volume, pages.
    
    Handles formats like:
    - "G. Thomas and M. J. Whelan, Phil. Mag. 4, 511 (1959)"
    - "PHYSICAL REVIEW MATERIALS 5, 083603 (2021)"
    - "Kinetic Theory of Dislocation Climb. I. General Models..."
    """
    result = {
        'authors': None,
        'year': None,
        'title': None,
        'journal': None,
        'volume': None,
        'page': None,
        'query': text.strip()
    }
    
    text = text.strip()
    if not text:
        return result
    
    # Extract year
    year_patterns = [
        r'\((\d{4})\)',  # (2021)
        r'\b(19\d{2}|20\d{2})\b',  # standalone year
    ]
    for pattern in year_patterns:
        match = re.search(pattern, text)
        if match:
            result['year'] = match.group(1)
            break
    
    # Extract volume and page numbers
    vol_page_patterns = [
        r'\b(\d+)\s*,\s*(\d+(?:[-–]\d+)?)\b',
        r'\b(\d+)\s*:\s*(\d+(?:[-–]\d+)?)\b',
        r'vol\.?\s*(\d+)\s*,?\s*(?:p\.?|pp\.?)?\s*(\d+(?:[-–]\d+)?)',
        r'\b(\d+)\s*\([\d]+\)\s*[:,]?\s*(\d+(?:[-–]\d+)?)',
    ]
    for pattern in vol_page_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['volume'] = match.group(1)
            result['page'] = match.group(2)
            break
    
    # Extract authors
    author_patterns = [
        # "G. Thomas and M. J. Whelan" - initials before surname
        r'^([A-Z]\.\s*(?:[A-Z]\.\s*)?[A-Za-z]+(?:\s+(?:and|&)\s+[A-Z]\.\s*(?:[A-Z]\.\s*)?[A-Za-z]+)*)',
        # "Thomas, G." or "Thomas, G. and Whelan, M. J."
        r'^([A-Za-z]+,?\s*[A-Z]\.(?:\s*[A-Z]\.)?(?:\s*(?:,|and|&)\s*[A-Za-z]+,?\s*[A-Z]\.(?:\s*[A-Z]\.)?)*)',
        # "Ji B, Gao H" - surname + initial without period
        r'^([A-Z][a-z]+\s+[A-Z](?:,\s*[A-Z][a-z]+\s+[A-Z])*)',
        # "Smith AB, Jones CD" - surname + initials without periods
        r'^([A-Z][a-z]+\s+[A-Z]{1,2}(?:,\s*[A-Z][a-z]+\s+[A-Z]{1,2})*)',
        # "et al."
        r'^([A-Za-z]+\s+et\s+al\.?)',
    ]
    
    for pattern in author_patterns:
        match = re.match(pattern, text)
        if match:
            result['authors'] = match.group(1).strip()
            remaining = text[match.end():].strip()
            if remaining.startswith(','):
                remaining = remaining[1:].strip()
            text = remaining
            break
    
    # Check for journal abbreviations
    # Need to match whole words/phrases, not substrings
    text_lower = text.lower()
    best_match = None
    best_match_len = 0
    
    for abbrev, full_name in JOURNAL_ABBREVIATIONS.items():
        if abbrev.startswith('_'):  # Skip comment entries
            continue
        # Create pattern that matches whole word/phrase
        # Escape special regex chars in abbreviation
        escaped_abbrev = re.escape(abbrev)
        # Match at word boundaries
        pattern = r'(?:^|[\s,;:])(' + escaped_abbrev + r')(?:[\s,;:\d]|$)'
        match = re.search(pattern, text_lower)
        if match:
            # Prefer longer matches (more specific)
            if len(abbrev) > best_match_len:
                best_match = full_name
                best_match_len = len(abbrev)
    
    if best_match:
        result['journal'] = best_match
    
    # Check for ALL CAPS journal name
    if not result['journal']:
        caps_match = re.match(r'^([A-Z][A-Z\s]+[A-Z])\b', text)
        if caps_match:
            journal_candidate = caps_match.group(1).strip()
            if len(journal_candidate) > 5 and ' ' in journal_candidate:
                result['journal'] = journal_candidate.title()
    
    # If no structured info found, treat as title
    if not result['authors'] and not result['journal'] and not result['volume']:
        result['title'] = text
    
    # Try to extract title from quotes
    title_patterns = [
        r'"([^"]+)"',
        r"'([^']+)'",
        r'(?:^|,\s*)([A-Z][^,]+(?:\.\s*[IVX]+\.)?[^,]*?)(?:,\s*(?:[A-Z]|$)|$)',
    ]
    
    if not result['title']:
        for pattern in title_patterns:
            match = re.search(pattern, text)
            if match:
                potential_title = match.group(1).strip()
                if len(potential_title) > 20 and not potential_title.replace(' ', '').isdigit():
                    result['title'] = potential_title
                    break
    
    return result


# ============== Formatting ==============

def format_search_result_short(item: Dict, index: int) -> str:
    """Format a search result for CLI display (compact)."""
    parts = [f"[{index}]"]
    
    if 'author' in item:
        authors = []
        for author in item['author'][:2]:
            name = author.get('family', '')
            if 'given' in author:
                name = f"{author['given'][0]}. {name}"
            authors.append(name)
        if len(item['author']) > 2:
            authors.append('et al.')
        parts.append(', '.join(authors))
    
    year = get_year(item)
    if year:
        parts.append(f"({year})")
    
    if 'title' in item and item['title']:
        title = item['title'][0] if isinstance(item['title'], list) else item['title']
        if len(title) > 60:
            title = title[:57] + '...'
        parts.append(f'"{title}"')
    
    if 'container-title' in item and item['container-title']:
        journal = item['container-title'][0] if isinstance(item['container-title'], list) else item['container-title']
        parts.append(journal)
    
    return ' '.join(parts)


def format_search_result_long(item: Dict) -> str:
    """Format a search result for GUI display (detailed)."""
    parts = []
    
    if 'author' in item:
        authors = []
        for author in item['author'][:3]:
            name = author.get('family', '')
            if 'given' in author:
                name = f"{author['given']} {name}"
            authors.append(name)
        if len(item['author']) > 3:
            authors.append('et al.')
        parts.append(', '.join(authors))
    
    year = get_year(item)
    if year:
        parts.append(f"({year})")
    
    if 'title' in item and item['title']:
        title = item['title'][0] if isinstance(item['title'], list) else item['title']
        if len(title) > 80:
            title = title[:77] + '...'
        parts.append(f'"{title}"')
    
    if 'container-title' in item and item['container-title']:
        journal = item['container-title'][0] if isinstance(item['container-title'], list) else item['container-title']
        parts.append(journal)
    
    vol_page = []
    if 'volume' in item:
        vol_page.append(f"vol. {item['volume']}")
    if 'page' in item:
        vol_page.append(f"p. {item['page']}")
    if vol_page:
        parts.append(', '.join(vol_page))
    
    return ' '.join(parts)


# ============== Clipboard ==============

def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard using platform-specific method."""
    system = platform.system()
    try:
        if system == 'Darwin':  # macOS
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
        elif system == 'Windows':
            process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
            process.communicate(text.encode('utf-8'))
        elif system == 'Linux':
            try:
                process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-8'))
            except FileNotFoundError:
                process = subprocess.Popen(['xsel', '--clipboard', '--input'], stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-8'))
        return True
    except Exception:
        return False


def copy_to_clipboard_tk(text: str, root) -> bool:
    """Copy text to clipboard using Tkinter (for GUI apps)."""
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        return True
    except Exception:
        return copy_to_clipboard(text)


# ============== Paper Download & Open ==============

def get_downloads_folder() -> str:
    """Get the standard Downloads folder for the current platform."""
    if platform.system() == 'Windows':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders') as key:
                return winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]
        except Exception:
            return os.path.join(os.path.expanduser('~'), 'Downloads')
    else:
        return os.path.join(os.path.expanduser('~'), 'Downloads')


def get_unpaywall_pdf_url(doi: str, email: str = "bibtexer@example.com") -> Optional[str]:
    """
    Query Unpaywall API to find open access PDF URL for a DOI.
    
    Unpaywall is a free service that finds legal open access versions of papers.
    Returns the PDF URL if found, None otherwise.
    """
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi, safe='')}?email={email}"
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', f'BibTexer/{__version__}')
    
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Check for best open access location
            best_oa = data.get('best_oa_location')
            if best_oa:
                pdf_url = best_oa.get('url_for_pdf')
                if pdf_url:
                    return pdf_url
                # Fallback to landing page URL
                return best_oa.get('url')
            
            # Check all OA locations
            oa_locations = data.get('oa_locations', [])
            for loc in oa_locations:
                pdf_url = loc.get('url_for_pdf')
                if pdf_url:
                    return pdf_url
            
            return None
    except Exception:
        return None


def download_pdf(url: str, doi: str, output_dir: Optional[str] = None) -> Optional[str]:
    """
    Download a PDF from URL to the specified directory.
    
    Returns the path to the downloaded file, or None if failed.
    """
    if output_dir is None:
        output_dir = get_downloads_folder()
    
    # Create a safe filename from DOI
    safe_doi = re.sub(r'[^\w\-.]', '_', doi)
    filename = f"{safe_doi}.pdf"
    filepath = os.path.join(output_dir, filename)
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', f'BibTexer/{__version__}')
    req.add_header('Accept', 'application/pdf,*/*')
    
    try:
        with urllib.request.urlopen(req, timeout=60, context=ssl_context) as response:
            content_type = response.headers.get('Content-Type', '')
            
            # Check if we got a PDF
            if 'pdf' not in content_type.lower() and not url.endswith('.pdf'):
                # Might be a redirect to HTML page, not a direct PDF
                return None
            
            with open(filepath, 'wb') as f:
                f.write(response.read())
            
            # Verify it's actually a PDF (check magic bytes)
            with open(filepath, 'rb') as f:
                header = f.read(5)
                if header != b'%PDF-':
                    os.remove(filepath)
                    return None
            
            return filepath
    except Exception:
        # Clean up partial download
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass
        return None


def open_file(filepath: str) -> bool:
    """Open a file with the system's default application."""
    try:
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', filepath], check=True)
        elif platform.system() == 'Windows':
            os.startfile(filepath)
        else:  # Linux
            subprocess.run(['xdg-open', filepath], check=True)
        return True
    except Exception:
        return False


def open_url(url: str) -> bool:
    """Open a URL in the system's default browser."""
    try:
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', url], check=True)
        elif platform.system() == 'Windows':
            os.startfile(url)
        else:  # Linux
            subprocess.run(['xdg-open', url], check=True)
        return True
    except Exception:
        return False


def get_doi_url(doi: str) -> str:
    """Get the standard DOI URL for a given DOI."""
    return f"https://doi.org/{doi}"


def try_download_paper(doi: str, output_dir: Optional[str] = None) -> Dict[str, any]:
    """
    Try to download a paper given its DOI.
    
    Returns a dict with:
        - success: bool - whether download succeeded
        - filepath: str or None - path to downloaded file
        - pdf_url: str or None - URL where PDF was found
        - doi_url: str - fallback DOI URL for browser
        - message: str - human-readable status message
    """
    result = {
        'success': False,
        'filepath': None,
        'pdf_url': None,
        'doi_url': get_doi_url(doi),
        'message': ''
    }
    
    # Try to find open access PDF via Unpaywall
    pdf_url = get_unpaywall_pdf_url(doi)
    
    if pdf_url:
        result['pdf_url'] = pdf_url
        
        # Try to download
        filepath = download_pdf(pdf_url, doi, output_dir)
        
        if filepath:
            result['success'] = True
            result['filepath'] = filepath
            result['message'] = f"Downloaded to {filepath}"
        else:
            result['message'] = "Found open access version but couldn't download PDF directly"
    else:
        result['message'] = "No open access version found"
    
    return result


def download_or_open_paper(doi: str, output_dir: Optional[str] = None, 
                           open_pdf: bool = True, fallback_browser: bool = True) -> Dict[str, any]:
    """
    Try to download paper, open it if successful, or fall back to browser.
    
    Args:
        doi: The DOI of the paper
        output_dir: Directory to save PDF (default: Downloads folder)
        open_pdf: Whether to open the PDF after download
        fallback_browser: Whether to open browser if download fails
    
    Returns dict with status information.
    """
    result = try_download_paper(doi, output_dir)
    
    if result['success'] and result['filepath']:
        if open_pdf:
            if open_file(result['filepath']):
                result['message'] += " and opened"
            else:
                result['message'] += " (couldn't open automatically)"
    elif fallback_browser:
        # Use the found PDF URL if available, otherwise DOI URL
        url_to_open = result.get('pdf_url') or result['doi_url']
        if open_url(url_to_open):
            result['opened_url'] = url_to_open
            result['message'] += f" - opened {url_to_open} in browser"
        else:
            result['message'] += f" - couldn't open browser"
    
    return result
