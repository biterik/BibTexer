#!/usr/bin/env python3
"""
BibTexer Core - Shared functionality for DOI/reference to BibTeX conversion

Part of the MatWerk Scholar Toolbox - Developed within NFDI-MatWerk (https://nfdi-matwerk.de/)
Copyright (c) 2026 Erik Bitzek
"""

__version__ = "2.1.0"
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
from typing import Optional, Dict, List


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
        with urllib.request.urlopen(req, timeout=30) as response:
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
        with urllib.request.urlopen(req, timeout=30) as response:
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
        r'^([A-Z]\.\s*(?:[A-Z]\.\s*)?[A-Za-z]+(?:\s+(?:and|&)\s+[A-Z]\.\s*(?:[A-Z]\.\s*)?[A-Za-z]+)*)',
        r'^([A-Za-z]+,?\s*[A-Z]\.(?:\s*[A-Z]\.)?(?:\s*(?:,|and|&)\s*[A-Za-z]+,?\s*[A-Z]\.(?:\s*[A-Z]\.)?)*)',
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
    text_lower = text.lower()
    for abbrev, full_name in JOURNAL_ABBREVIATIONS.items():
        if text_lower.startswith(abbrev) or abbrev in text_lower:
            result['journal'] = full_name
            break
    
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
