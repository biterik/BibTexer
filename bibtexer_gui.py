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


class BibTexerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("BibTexer - DOI to BibTeX Converter")
        self.geometry("700x550")
        self.minsize(500, 400)
        
        # Set appearance
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        
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
            text="Convert DOI to BibTeX using CrossRef API",
            font=ctk.CTkFont(size=12)
        )
        self.subtitle_label.pack(pady=(0, 15))
        
        # Input frame
        self.input_frame = ctk.CTkFrame(self.main_frame)
        self.input_frame.pack(fill="x", padx=10, pady=5)
        
        self.doi_label = ctk.CTkLabel(
            self.input_frame, 
            text="Enter DOI:",
            font=ctk.CTkFont(size=14)
        )
        self.doi_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # DOI entry with button frame
        self.entry_button_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.entry_button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.doi_entry = ctk.CTkEntry(
            self.entry_button_frame, 
            placeholder_text="e.g., 10.1038/nature12373 or https://doi.org/...",
            height=40,
            font=ctk.CTkFont(size=13)
        )
        self.doi_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.doi_entry.bind("<Return>", lambda e: self.convert_doi())
        
        self.convert_button = ctk.CTkButton(
            self.entry_button_frame, 
            text="Convert",
            command=self.convert_doi,
            height=40,
            width=100,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.convert_button.pack(side="right")
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.main_frame, 
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=5)
        
        # Output frame
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
        
        # Button frame
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
        
        # Store current bibtex
        self.current_bibtex = ""
    
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
        self.output_text.delete("1.0", "end")
        self.current_bibtex = ""
        self.set_status("", "info")


def main():
    app = BibTexerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
