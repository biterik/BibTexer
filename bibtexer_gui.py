#!/usr/bin/env python3
"""
BibTexer GUI - A cross-platform GUI tool to convert DOI to BibTeX entry using CrossRef API

Requirements: pip install customtkinter
"""

import sys
import subprocess
import platform
import urllib.request
import urllib.parse
import urllib.error
import json
import re
import unicodedata
import threading
from typing import Optional, Dict, List, Tuple

try:
    import customtkinter as ctk
except ImportError:
    print("CustomTkinter not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
    import customtkinter as ctk


def normalize_text(text):
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


def get_crossref_data(doi):
    """Fetch metadata from CrossRef API for a given DOI."""
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'BibTexer/1.0 (mailto:user@example.com)')
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


def format_authors(authors):
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


def generate_cite_key(data):
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


def get_year(data):
    """Extract publication year from data."""
    for date_field in ['published-print', 'published-online', 'issued', 'created']:
        if date_field in data and 'date-parts' in data[date_field]:
            date_parts = data[date_field]['date-parts']
            if date_parts and date_parts[0] and date_parts[0][0]:
                return str(date_parts[0][0])
    return None


def get_month(data):
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


def get_entry_type(data):
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


def convert_to_bibtex(data):
    """Convert CrossRef metadata to BibTeX entry."""
    entry_type = get_entry_type(data)
    cite_key = generate_cite_key(data)
    
    fields = {}
    
    if 'title' in data and data['title']:
        title = data['title'][0] if isinstance(data['title'], list) else data['title']
        fields['title'] = f"{{{normalize_text(title)}}}"
    
    authors = format_authors(data.get('author', []))
    if authors:
        fields['author'] = f"{{{normalize_text(authors)}}}"
    
    editors = format_authors(data.get('editor', []))
    if editors:
        fields['editor'] = f"{{{normalize_text(editors)}}}"
    
    year = get_year(data)
    if year:
        fields['year'] = f"{{{year}}}"
    
    month = get_month(data)
    if month:
        fields['month'] = month
    
    if 'container-title' in data and data['container-title']:
        container = data['container-title'][0] if isinstance(data['container-title'], list) else data['container-title']
        if entry_type == 'article':
            fields['journal'] = f"{{{normalize_text(container)}}}"
        elif entry_type in ['incollection', 'inproceedings']:
            fields['booktitle'] = f"{{{normalize_text(container)}}}"
    
    if 'volume' in data and data['volume']:
        fields['volume'] = f"{{{data['volume']}}}"
    
    if 'issue' in data and data['issue']:
        fields['number'] = f"{{{data['issue']}}}"
    
    if 'page' in data and data['page']:
        pages = data['page'].replace('-', '--')
        fields['pages'] = f"{{{pages}}}"
    
    if 'DOI' in data:
        fields['doi'] = f"{{{data['DOI']}}}"
    
    if 'URL' in data:
        fields['url'] = f"{{{data['URL']}}}"
    
    if 'publisher' in data and data['publisher']:
        fields['publisher'] = f"{{{normalize_text(data['publisher'])}}}"
    
    if 'ISSN' in data and data['ISSN']:
        issn = data['ISSN'][0] if isinstance(data['ISSN'], list) else data['ISSN']
        fields['issn'] = f"{{{issn}}}"
    
    if 'ISBN' in data and data['ISBN']:
        isbn = data['ISBN'][0] if isinstance(data['ISBN'], list) else data['ISBN']
        fields['isbn'] = f"{{{isbn}}}"
    
    if 'abstract' in data and data['abstract']:
        abstract = re.sub(r'<[^>]+>', '', data['abstract'])
        fields['abstract'] = f"{{{normalize_text(abstract)}}}"
    
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


def copy_to_clipboard_cross_platform(text, root):
    """Copy text to clipboard using cross-platform method."""
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()  # Required for clipboard to persist
        return True
    except Exception:
        # Fallback for different platforms
        system = platform.system()
        try:
            if system == 'Darwin':  # macOS
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-8'))
            elif system == 'Windows':
                process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
                process.communicate(text.encode('utf-8'))
            elif system == 'Linux':
                # Try xclip first, then xsel
                try:
                    process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
                    process.communicate(text.encode('utf-8'))
                except FileNotFoundError:
                    process = subprocess.Popen(['xsel', '--clipboard', '--input'], stdin=subprocess.PIPE)
                    process.communicate(text.encode('utf-8'))
            return True
        except Exception:
            return False


# ============== Reference Parser ==============

# Common journal abbreviations mapping
JOURNAL_ABBREVIATIONS = {
    'phil. mag.': 'Philosophical Magazine',
    'phil mag': 'Philosophical Magazine',
    'phys. rev.': 'Physical Review',
    'phys rev': 'Physical Review',
    'phys. rev. lett.': 'Physical Review Letters',
    'phys. rev. b': 'Physical Review B',
    'phys. rev. materials': 'Physical Review Materials',
    'j. appl. phys.': 'Journal of Applied Physics',
    'j appl phys': 'Journal of Applied Physics',
    'acta mater.': 'Acta Materialia',
    'acta metall.': 'Acta Metallurgica',
    'mater. sci. eng.': 'Materials Science and Engineering',
    'int. j.': 'International Journal',
    'j. mech. phys. solids': 'Journal of the Mechanics and Physics of Solids',
    'comput. mater. sci.': 'Computational Materials Science',
    'model. simul. mater. sci. eng.': 'Modelling and Simulation in Materials Science and Engineering',
    'nature': 'Nature',
    'science': 'Science',
    'pnas': 'Proceedings of the National Academy of Sciences',
    'proc. natl. acad. sci.': 'Proceedings of the National Academy of Sciences',
}


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
        'query': text.strip()  # Keep original for fallback search
    }
    
    text = text.strip()
    if not text:
        return result
    
    # Try to extract year (typically in parentheses or as 4-digit number)
    year_patterns = [
        r'\((\d{4})\)',  # (2021)
        r'\b(19\d{2}|20\d{2})\b',  # standalone year
    ]
    for pattern in year_patterns:
        match = re.search(pattern, text)
        if match:
            result['year'] = match.group(1)
            break
    
    # Try to extract volume and page numbers
    # Pattern: volume, page or volume: page or vol. X, p. Y
    vol_page_patterns = [
        r'\b(\d+)\s*,\s*(\d+(?:[-–]\d+)?)\b',  # 5, 083603 or 4, 511-520
        r'\b(\d+)\s*:\s*(\d+(?:[-–]\d+)?)\b',  # 5:083603
        r'vol\.?\s*(\d+)\s*,?\s*(?:p\.?|pp\.?)?\s*(\d+(?:[-–]\d+)?)',  # vol. 5, p. 100
        r'\b(\d+)\s*\([\d]+\)\s*[:,]?\s*(\d+(?:[-–]\d+)?)',  # 5(3):100 or 5(3), 100
    ]
    for pattern in vol_page_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['volume'] = match.group(1)
            result['page'] = match.group(2)
            break
    
    # Try to detect if this is author-style reference (contains "and" or initials pattern)
    author_patterns = [
        r'^([A-Z]\.\s*(?:[A-Z]\.\s*)?[A-Za-z]+(?:\s+(?:and|&)\s+[A-Z]\.\s*(?:[A-Z]\.\s*)?[A-Za-z]+)*)',  # G. Thomas and M. J. Whelan
        r'^([A-Za-z]+,?\s*[A-Z]\.(?:\s*[A-Z]\.)?(?:\s*(?:,|and|&)\s*[A-Za-z]+,?\s*[A-Z]\.(?:\s*[A-Z]\.)?)*)',  # Thomas, G. and Whelan, M. J.
        r'^([A-Za-z]+\s+et\s+al\.?)',  # Smith et al.
    ]
    
    for pattern in author_patterns:
        match = re.match(pattern, text)
        if match:
            result['authors'] = match.group(1).strip()
            # Remove authors from text for further parsing
            remaining = text[match.end():].strip()
            if remaining.startswith(','):
                remaining = remaining[1:].strip()
            text = remaining
            break
    
    # Try to identify journal name
    # Check if text starts with known journal (all caps or known abbreviation)
    text_lower = text.lower()
    
    # Check for known abbreviations
    for abbrev, full_name in JOURNAL_ABBREVIATIONS.items():
        if text_lower.startswith(abbrev) or abbrev in text_lower:
            result['journal'] = full_name
            break
    
    # Check for ALL CAPS journal name pattern (like "PHYSICAL REVIEW MATERIALS")
    if not result['journal']:
        caps_match = re.match(r'^([A-Z][A-Z\s]+[A-Z])\b', text)
        if caps_match:
            journal_candidate = caps_match.group(1).strip()
            # Verify it's likely a journal (more than one word, not just "I" or "II")
            if len(journal_candidate) > 5 and ' ' in journal_candidate:
                result['journal'] = journal_candidate.title()
    
    # If no journal found and no authors, this might be a title-only search
    if not result['authors'] and not result['journal'] and not result['volume']:
        # Assume the entire text is a title
        result['title'] = text
    
    # Try to extract title (often in quotes or between commas after authors)
    title_patterns = [
        r'"([^"]+)"',  # "Title in quotes"
        r"'([^']+)'",  # 'Title in single quotes'
        r'(?:^|,\s*)([A-Z][^,]+(?:\.\s*[IVX]+\.)?[^,]*?)(?:,\s*(?:[A-Z]|$)|$)',  # Title starting with capital
    ]
    
    if not result['title']:
        for pattern in title_patterns:
            match = re.search(pattern, text)
            if match:
                potential_title = match.group(1).strip()
                # Make sure it's not just a journal name or numbers
                if len(potential_title) > 20 and not potential_title.replace(' ', '').isdigit():
                    result['title'] = potential_title
                    break
    
    return result


def search_crossref(query: Optional[str] = None, author: Optional[str] = None, title: Optional[str] = None, 
                    journal: Optional[str] = None, year: Optional[str] = None, rows: int = 10) -> List[Dict]:
    """
    Search CrossRef API for references matching the given criteria.
    
    Returns a list of matching items with their metadata.
    """
    base_url = "https://api.crossref.org/works"
    params = {'rows': str(rows)}
    
    # Build query string
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
    
    # Add bibliographic filter if we have specific info
    filters = []
    if year:
        filters.append(f'from-pub-date:{year}')
        filters.append(f'until-pub-date:{year}')
    
    if filters:
        params['filter'] = ','.join(filters)
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'BibTexer/1.0 (mailto:user@example.com)')
    req.add_header('Accept', 'application/json')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data['message'].get('items', [])
    except Exception as e:
        raise ValueError(f"Search failed: {e}")


def format_search_result(item: Dict) -> str:
    """Format a CrossRef search result for display."""
    parts = []
    
    # Authors
    if 'author' in item:
        authors = []
        for author in item['author'][:3]:  # First 3 authors
            name = author.get('family', '')
            if 'given' in author:
                name = f"{author['given']} {name}"
            authors.append(name)
        if len(item['author']) > 3:
            authors.append('et al.')
        parts.append(', '.join(authors))
    
    # Year
    year = get_year(item)
    if year:
        parts.append(f"({year})")
    
    # Title
    if 'title' in item and item['title']:
        title = item['title'][0] if isinstance(item['title'], list) else item['title']
        if len(title) > 80:
            title = title[:77] + '...'
        parts.append(f'"{title}"')
    
    # Journal
    if 'container-title' in item and item['container-title']:
        journal = item['container-title'][0] if isinstance(item['container-title'], list) else item['container-title']
        parts.append(journal)
    
    # Volume and page
    vol_page = []
    if 'volume' in item:
        vol_page.append(f"vol. {item['volume']}")
    if 'page' in item:
        vol_page.append(f"p. {item['page']}")
    if vol_page:
        parts.append(', '.join(vol_page))
    
    return ' '.join(parts)


# ============== Search Results Dialog ==============

class SearchResultsDialog(ctk.CTkToplevel):
    """Dialog to display and select from search results."""
    
    def __init__(self, parent, results: List[Dict]):
        super().__init__(parent)
        
        self.results = results
        self.selected_item = None
        
        self.title("Select Reference")
        self.geometry("800x500")
        self.minsize(600, 400)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Title
        title_label = ctk.CTkLabel(
            self,
            text=f"Found {len(results)} matching references",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(15, 10))
        
        instruction_label = ctk.CTkLabel(
            self,
            text="Double-click or select and click 'Use Selected' to choose a reference",
            font=ctk.CTkFont(size=12)
        )
        instruction_label.pack(pady=(0, 10))
        
        # Results list frame
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Scrollable frame for results
        self.scrollable_frame = ctk.CTkScrollableFrame(list_frame)
        self.scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create result items
        self.result_buttons = []
        for i, item in enumerate(results):
            formatted = format_search_result(item)
            
            btn = ctk.CTkButton(
                self.scrollable_frame,
                text=formatted,
                anchor="w",
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray30"),
                height=50,
                command=lambda idx=i: self.select_result(idx)
            )
            btn.pack(fill="x", padx=5, pady=2)
            btn.bind("<Double-Button-1>", lambda e, idx=i: self.confirm_selection(idx))
            self.result_buttons.append(btn)
        
        # Button frame
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=15)
        
        self.use_button = ctk.CTkButton(
            button_frame,
            text="Use Selected",
            command=self.use_selected,
            state="disabled",
            font=ctk.CTkFont(size=13)
        )
        self.use_button.pack(side="left", padx=(0, 10))
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.cancel,
            fg_color="gray",
            font=ctk.CTkFont(size=13)
        )
        cancel_button.pack(side="left")
        
        self.selected_index = None
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def select_result(self, index: int):
        """Highlight selected result."""
        # Reset all buttons
        for btn in self.result_buttons:
            btn.configure(fg_color="transparent")
        
        # Highlight selected
        self.result_buttons[index].configure(fg_color=("gray70", "gray40"))
        self.selected_index = index
        self.use_button.configure(state="normal")
    
    def confirm_selection(self, index: int):
        """Confirm selection on double-click."""
        self.selected_index = index
        self.use_selected()
    
    def use_selected(self):
        """Use the selected result."""
        if self.selected_index is not None:
            self.selected_item = self.results[self.selected_index]
            self.destroy()
    
    def cancel(self):
        """Cancel the dialog."""
        self.selected_item = None
        self.destroy()


class BibTexerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("BibTexer - DOI to BibTeX Converter")
        self.geometry("750x650")
        self.minsize(600, 500)
        
        # Set appearance
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        
        # Store current bibtex
        self.current_bibtex = ""
        
        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title label
        self.title_label = ctk.CTkLabel(
            self.main_frame, 
            text="BibTexer", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(10, 5))
        
        self.subtitle_label = ctk.CTkLabel(
            self.main_frame, 
            text="Convert references to BibTeX using CrossRef API",
            font=ctk.CTkFont(size=12)
        )
        self.subtitle_label.pack(pady=(0, 10))
        
        # Create tabview
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add tabs
        self.tab_doi = self.tabview.add("DOI Lookup")
        self.tab_search = self.tabview.add("Reference Search")
        
        # Setup DOI tab
        self._setup_doi_tab()
        
        # Setup Search tab
        self._setup_search_tab()
        
        # Status label (shared)
        self.status_label = ctk.CTkLabel(
            self.main_frame, 
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=5)
        
        # Output frame (shared)
        self.output_frame = ctk.CTkFrame(self.main_frame)
        self.output_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.output_label = ctk.CTkLabel(
            self.output_frame, 
            text="BibTeX Output:",
            font=ctk.CTkFont(size=14)
        )
        self.output_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.output_text = ctk.CTkTextbox(
            self.output_frame, 
            font=ctk.CTkFont(family="Courier", size=12),
            wrap="word"
        )
        self.output_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Button frame (shared)
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.copy_button = ctk.CTkButton(
            self.button_frame, 
            text="Copy to Clipboard",
            command=self.copy_to_clipboard,
            height=35,
            font=ctk.CTkFont(size=13)
        )
        self.copy_button.pack(side="left", padx=(0, 10))
        
        self.clear_button = ctk.CTkButton(
            self.button_frame, 
            text="Clear",
            command=self.clear_all,
            height=35,
            fg_color="gray",
            font=ctk.CTkFont(size=13)
        )
        self.clear_button.pack(side="left")
        
        # Theme toggle
        self.theme_switch = ctk.CTkSwitch(
            self.button_frame,
            text="Dark Mode",
            command=self.toggle_theme,
            font=ctk.CTkFont(size=12)
        )
        self.theme_switch.pack(side="right")
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()
    
    def _setup_doi_tab(self):
        """Setup the DOI lookup tab."""
        # DOI input frame
        doi_frame = ctk.CTkFrame(self.tab_doi)
        doi_frame.pack(fill="x", padx=10, pady=10)
        
        doi_label = ctk.CTkLabel(
            doi_frame, 
            text="Enter DOI:",
            font=ctk.CTkFont(size=14)
        )
        doi_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        entry_button_frame = ctk.CTkFrame(doi_frame, fg_color="transparent")
        entry_button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.doi_entry = ctk.CTkEntry(
            entry_button_frame, 
            placeholder_text="e.g., 10.1038/nature12373 or https://doi.org/...",
            height=40,
            font=ctk.CTkFont(size=13)
        )
        self.doi_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.doi_entry.bind("<Return>", lambda e: self.convert_doi())
        
        self.convert_button = ctk.CTkButton(
            entry_button_frame, 
            text="Convert",
            command=self.convert_doi,
            height=40,
            width=100,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.convert_button.pack(side="right")
    
    def _setup_search_tab(self):
        """Setup the reference search tab."""
        # Search input frame
        search_frame = ctk.CTkFrame(self.tab_search)
        search_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Instructions
        instruction_label = ctk.CTkLabel(
            search_frame, 
            text="Enter any reference information (authors, title, journal, year, etc.):",
            font=ctk.CTkFont(size=14)
        )
        instruction_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Examples
        examples_text = """Examples:
• G. Thomas and M. J. Whelan, Phil. Mag. 4, 511 (1959)
• PHYSICAL REVIEW MATERIALS 5, 083603 (2021)
• Kinetic Theory of Dislocation Climb. I. General Models for Edge and Screw Dislocations"""
        
        examples_label = ctk.CTkLabel(
            search_frame, 
            text=examples_text,
            font=ctk.CTkFont(size=11),
            justify="left",
            text_color="gray"
        )
        examples_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Search text entry (multiline)
        self.search_entry = ctk.CTkTextbox(
            search_frame, 
            height=80,
            font=ctk.CTkFont(size=13),
            wrap="word"
        )
        self.search_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        # Search button frame
        search_button_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.search_button = ctk.CTkButton(
            search_button_frame, 
            text="Search CrossRef",
            command=self.search_reference,
            height=40,
            width=150,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.search_button.pack(side="left")
        
        # Parsed info display
        self.parsed_label = ctk.CTkLabel(
            search_frame, 
            text="",
            font=ctk.CTkFont(size=11),
            justify="left",
            text_color="gray"
        )
        self.parsed_label.pack(anchor="w", padx=10, pady=(5, 5))
    
    def toggle_theme(self):
        if self.theme_switch.get():
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")
    
    def convert_doi(self):
        doi = self.doi_entry.get().strip()
        
        if not doi:
            self.set_status("Please enter a DOI", "warning")
            return
        
        # Clean up DOI
        doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
        doi = re.sub(r'^doi:', '', doi, flags=re.IGNORECASE)
        
        # Disable button and show loading
        self.convert_button.configure(state="disabled", text="Loading...")
        self.set_status("Fetching data from CrossRef...", "info")
        
        # Run in thread to prevent GUI freeze
        thread = threading.Thread(target=self._fetch_and_convert, args=(doi,))
        thread.start()
    
    def _fetch_and_convert(self, doi):
        try:
            data = get_crossref_data(doi)
            bibtex = convert_to_bibtex(data)
            self.current_bibtex = bibtex
            
            # Update GUI in main thread
            self.after(0, lambda: self._update_output(bibtex))
            self.after(0, lambda: self.set_status("✓ Successfully converted!", "success"))
        except ValueError as e:
            self.after(0, lambda: self.set_status(f"Error: {e}", "error"))
            self.after(0, lambda: self._update_output(""))
        except Exception as e:
            self.after(0, lambda: self.set_status(f"Unexpected error: {e}", "error"))
            self.after(0, lambda: self._update_output(""))
        finally:
            self.after(0, lambda: self.convert_button.configure(state="normal", text="Convert"))
    
    def search_reference(self):
        """Search for a reference using parsed information."""
        search_text = self.search_entry.get("1.0", "end").strip()
        
        if not search_text:
            self.set_status("Please enter reference information", "warning")
            return
        
        # Parse the reference
        parsed = parse_reference(search_text)
        
        # Show parsed info
        parsed_parts = []
        if parsed['authors']:
            parsed_parts.append(f"Authors: {parsed['authors']}")
        if parsed['year']:
            parsed_parts.append(f"Year: {parsed['year']}")
        if parsed['journal']:
            parsed_parts.append(f"Journal: {parsed['journal']}")
        if parsed['title']:
            title_display = parsed['title'][:50] + '...' if len(parsed['title'] or '') > 50 else parsed['title']
            parsed_parts.append(f"Title: {title_display}")
        if parsed['volume']:
            parsed_parts.append(f"Vol: {parsed['volume']}")
        if parsed['page']:
            parsed_parts.append(f"Page: {parsed['page']}")
        
        if parsed_parts:
            self.parsed_label.configure(text="Parsed: " + " | ".join(parsed_parts))
        else:
            self.parsed_label.configure(text="Will search using full text")
        
        # Disable button and show loading
        self.search_button.configure(state="disabled", text="Searching...")
        self.set_status("Searching CrossRef...", "info")
        
        # Run search in thread
        thread = threading.Thread(target=self._perform_search, args=(parsed,))
        thread.start()
    
    def _perform_search(self, parsed: Dict):
        """Perform the CrossRef search in a background thread."""
        try:
            # Build search parameters
            results = search_crossref(
                query=parsed['query'] if not parsed['title'] and not parsed['authors'] else None,
                author=parsed['authors'],
                title=parsed['title'],
                journal=parsed['journal'],
                year=parsed['year'],
                rows=15
            )
            
            if not results:
                self.after(0, lambda: self.set_status("No results found", "warning"))
                self.after(0, lambda: self._update_output(""))
                return
            
            if len(results) == 1:
                # Only one result, use it directly
                bibtex = convert_to_bibtex(results[0])
                self.current_bibtex = bibtex
                self.after(0, lambda: self._update_output(bibtex))
                self.after(0, lambda: self.set_status("✓ Found 1 matching reference!", "success"))
            else:
                # Multiple results, show selection dialog
                self.after(0, lambda: self._show_search_results(results))
                
        except ValueError as e:
            self.after(0, lambda: self.set_status(f"Error: {e}", "error"))
        except Exception as e:
            self.after(0, lambda: self.set_status(f"Unexpected error: {e}", "error"))
        finally:
            self.after(0, lambda: self.search_button.configure(state="normal", text="Search CrossRef"))
    
    def _show_search_results(self, results: List[Dict]):
        """Show the search results dialog."""
        self.set_status(f"Found {len(results)} matches - please select one", "info")
        
        dialog = SearchResultsDialog(self, results)
        self.wait_window(dialog)
        
        if dialog.selected_item:
            bibtex = convert_to_bibtex(dialog.selected_item)
            self.current_bibtex = bibtex
            self._update_output(bibtex)
            self.set_status("✓ Successfully converted selected reference!", "success")
    
    def _update_output(self, text):
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", text)
    
    def set_status(self, message, status_type="info"):
        colors = {
            "info": ("gray", "gray"),
            "success": ("green", "#00AA00"),
            "warning": ("orange", "#FF8800"),
            "error": ("red", "#CC0000")
        }
        color = colors.get(status_type, colors["info"])
        self.status_label.configure(text=message, text_color=color[1 if ctk.get_appearance_mode() == "Dark" else 0])
    
    def copy_to_clipboard(self):
        if self.current_bibtex:
            if copy_to_clipboard_cross_platform(self.current_bibtex, self):
                self.set_status("✓ Copied to clipboard!", "success")
            else:
                self.set_status("⚠ Could not copy to clipboard", "warning")
        else:
            self.set_status("Nothing to copy", "warning")
    
    def clear_all(self):
        self.doi_entry.delete(0, "end")
        self.search_entry.delete("1.0", "end")
        self.output_text.delete("1.0", "end")
        self.parsed_label.configure(text="")
        self.current_bibtex = ""
        self.set_status("", "info")


def main():
    app = BibTexerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
