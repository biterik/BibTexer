#!/usr/bin/env python3
"""
BibTexer GUI - A cross-platform GUI tool to convert DOI to BibTeX entry

Part of the MatWerk Scholar Toolbox - Developed within NFDI-MatWerk (https://nfdi-matwerk.de/)
Copyright (c) 2026 Erik Bitzek

Requirements: pip install customtkinter
"""

import sys
import subprocess
import threading
import tkinter as tk
from typing import List, Dict

try:
    import customtkinter as ctk
except ImportError:
    print("CustomTkinter not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
    import customtkinter as ctk

from bibtexer_core import (
    __version__,
    clean_doi,
    get_crossref_data,
    search_crossref,
    convert_to_bibtex,
    convert_to_ris,
    parse_reference,
    format_search_result_long,
    copy_to_clipboard_tk,
    download_or_open_paper,
    open_url,
    get_doi_url,
    is_zotero_running,
    send_to_zotero_local,
)


class SearchResultsFrame(ctk.CTkFrame):
    """Frame to display search results inline (replaces popup dialog)."""
    
    def __init__(self, parent, results: List[Dict], callback):
        super().__init__(parent)
        
        self.results = results
        self.selected_item = None
        self.selected_index = None
        self.callback = callback  # Called when selection is made or cancelled
        
        # Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = ctk.CTkLabel(
            title_frame,
            text=f"Found {len(results)} matching references - select one:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.pack(side="left")
        
        cancel_button = ctk.CTkButton(
            title_frame,
            text="✕ Cancel",
            command=self.cancel,
            width=80,
            height=28,
            fg_color="gray",
            font=ctk.CTkFont(size=12)
        )
        cancel_button.pack(side="right")
        
        # Scrollable results list
        self.scrollable_frame = ctk.CTkScrollableFrame(self, height=200)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create result items
        self.result_buttons = []
        for i, item in enumerate(results):
            formatted = format_search_result_long(item)
            
            btn = ctk.CTkButton(
                self.scrollable_frame,
                text=formatted,
                anchor="w",
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray30"),
                height=45,
                command=lambda idx=i: self.select_result(idx)
            )
            btn.pack(fill="x", padx=5, pady=2)
            btn.bind("<Double-Button-1>", lambda e, idx=i: self.confirm_selection(idx))
            self.result_buttons.append(btn)
        
        # Use Selected button
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.use_button = ctk.CTkButton(
            button_frame,
            text="Use Selected",
            command=self.use_selected,
            state="disabled",
            font=ctk.CTkFont(size=13)
        )
        self.use_button.pack(side="left")
    
    def select_result(self, index: int):
        """Highlight selected result."""
        for btn in self.result_buttons:
            btn.configure(fg_color="transparent")
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
            self.callback(self.selected_item)
            self.destroy()
    
    def cancel(self):
        """Cancel the selection."""
        self.selected_item = None
        self.callback(None)
        self.destroy()


class BibTexerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title(f"BibTexer v{__version__} - DOI to BibTeX Converter")
        self.geometry("850x700")
        self.minsize(700, 500)
        
        # Set appearance
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        
        # Store current data
        self.current_bibtex = ""
        self.current_ris = ""
        self.current_doi = None
        self.current_crossref_data = None  # Store raw CrossRef data for Zotero
        
        # Create scrollable main frame for smaller screens
        self.main_frame = ctk.CTkScrollableFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Title label
        self.title_label = ctk.CTkLabel(
            self.main_frame, 
            text="BibTexer", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(10, 5))
        
        self.subtitle_label = ctk.CTkLabel(
            self.main_frame, 
            text="Convert references to BibTeX/RIS • Download papers • Add to Zotero",
            font=ctk.CTkFont(size=12)
        )
        self.subtitle_label.pack(pady=(0, 5))
        
        # NFDI-MatWerk attribution
        self.attribution_label = ctk.CTkLabel(
            self.main_frame, 
            text="Part of the MatWerk Scholar Toolbox • NFDI-MatWerk",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.attribution_label.pack(pady=(0, 10))
        
        # Create tabview
        self.tabview = ctk.CTkTabview(self.main_frame, height=180)
        self.tabview.pack(fill="x", padx=10, pady=5)
        
        # Add tabs
        self.tab_doi = self.tabview.add("DOI Lookup")
        self.tab_search = self.tabview.add("Reference Search")
        
        # Set Reference Search as default tab
        self.tabview.set("Reference Search")
        
        # Setup tabs
        self._setup_doi_tab()
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
        self.output_frame.pack(fill="x", padx=10, pady=5)
        
        # Output label and format selector in same row
        output_header_frame = ctk.CTkFrame(self.output_frame, fg_color="transparent")
        output_header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.output_label = ctk.CTkLabel(
            output_header_frame, 
            text="Output:",
            font=ctk.CTkFont(size=14)
        )
        self.output_label.pack(side="left")
        
        # Format selector (radio buttons)
        self.format_var = ctk.StringVar(value="bibtex")
        
        format_frame = ctk.CTkFrame(output_header_frame, fg_color="transparent")
        format_frame.pack(side="right")
        
        format_label = ctk.CTkLabel(
            format_frame,
            text="Format:",
            font=ctk.CTkFont(size=12)
        )
        format_label.pack(side="left", padx=(0, 10))
        
        self.bibtex_radio = ctk.CTkRadioButton(
            format_frame,
            text="BibTeX",
            variable=self.format_var,
            value="bibtex",
            command=self._on_format_change,
            font=ctk.CTkFont(size=12)
        )
        self.bibtex_radio.pack(side="left", padx=(0, 10))
        
        self.ris_radio = ctk.CTkRadioButton(
            format_frame,
            text="RIS",
            variable=self.format_var,
            value="ris",
            command=self._on_format_change,
            font=ctk.CTkFont(size=12)
        )
        self.ris_radio.pack(side="left")
        
        self.output_text = ctk.CTkTextbox(
            self.output_frame, 
            font=ctk.CTkFont(family="Courier", size=12),
            wrap="word",
            height=200
        )
        self.output_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # Button frame (shared)
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.pack(fill="x", padx=15, pady=(10, 5))
        
        self.copy_button = ctk.CTkButton(
            self.button_frame, 
            text="📋 Copy",
            command=self.copy_to_clipboard,
            height=35,
            width=100,
            font=ctk.CTkFont(size=13)
        )
        self.copy_button.pack(side="left", padx=(0, 8))
        
        self.oa_button = ctk.CTkButton(
            self.button_frame, 
            text="📄 Open Access",
            command=self.download_open_access,
            height=35,
            font=ctk.CTkFont(size=13),
            fg_color="#28a745",
            width=130
        )
        self.oa_button.pack(side="left", padx=(0, 8))
        
        self.journal_button = ctk.CTkButton(
            self.button_frame, 
            text="🏛️ Journal",
            command=self.open_journal_page,
            height=35,
            font=ctk.CTkFont(size=13),
            fg_color="#0066cc",
            width=110
        )
        self.journal_button.pack(side="left", padx=(0, 8))
        
        self.clear_button = ctk.CTkButton(
            self.button_frame, 
            text="Clear",
            command=self.clear_all,
            height=35,
            width=80,
            fg_color="gray",
            font=ctk.CTkFont(size=13)
        )
        self.clear_button.pack(side="left", padx=(0, 15))
        
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
        
        # Export section (NEW in v4.0)
        self._setup_export_section()
    
    def _setup_export_section(self):
        """Setup the export section with Zotero integration."""
        # Separator
        separator_frame = ctk.CTkFrame(self.main_frame, height=2, fg_color="gray70")
        separator_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        # Export section label
        export_label = ctk.CTkLabel(
            self.main_frame,
            text="Export",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray"
        )
        export_label.pack(pady=(5, 5))
        
        # Export button frame
        export_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        export_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.zotero_button = ctk.CTkButton(
            export_frame,
            text="📚 Add to Zotero",
            command=self.add_to_zotero,
            height=35,
            width=150,
            font=ctk.CTkFont(size=13),
            fg_color="#cc2936"
        )
        self.zotero_button.pack(side="left", padx=(0, 10))
        
        # Zotero status indicator
        self.zotero_status_label = ctk.CTkLabel(
            export_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.zotero_status_label.pack(side="left")
        
        # Check Zotero status on startup
        self._check_zotero_status()
    
    def _check_zotero_status(self):
        """Check if Zotero is running and update status."""
        def check():
            running = is_zotero_running()
            status_text = "● Zotero detected" if running else "○ Zotero not running"
            status_color = "#28a745" if running else "gray"
            self.after(0, lambda: self.zotero_status_label.configure(
                text=status_text, 
                text_color=status_color
            ))
        
        thread = threading.Thread(target=check)
        thread.start()
    
    def _setup_doi_tab(self):
        """Setup the DOI lookup tab."""
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
        search_frame = ctk.CTkFrame(self.tab_search)
        search_frame.pack(fill="x", padx=10, pady=10)
        
        instruction_label = ctk.CTkLabel(
            search_frame, 
            text="Enter any reference information (authors, title, journal, year, etc.):",
            font=ctk.CTkFont(size=14)
        )
        instruction_label.pack(anchor="w", padx=10, pady=(10, 5))
        
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
        
        self.search_entry = ctk.CTkTextbox(
            search_frame, 
            height=80,
            font=ctk.CTkFont(size=13),
            wrap="word"
        )
        self.search_entry.pack(fill="x", padx=10, pady=(0, 10))
        
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
        
        self.parsed_label = ctk.CTkLabel(
            search_frame, 
            text="",
            font=ctk.CTkFont(size=11),
            justify="left",
            text_color="gray"
        )
        self.parsed_label.pack(anchor="w", padx=10, pady=(5, 5))
    
    def _on_format_change(self):
        """Handle format radio button change."""
        self._update_output_display()
    
    def _update_output_display(self):
        """Update the output text based on selected format."""
        if self.format_var.get() == "bibtex":
            self._update_output(self.current_bibtex)
        else:
            self._update_output(self.current_ris)
    
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
        
        doi = clean_doi(doi)
        
        self.convert_button.configure(state="disabled", text="Loading...")
        self.set_status("Fetching data from CrossRef...", "info")
        
        thread = threading.Thread(target=self._fetch_and_convert, args=(doi,))
        thread.start()
    
    def _fetch_and_convert(self, doi):
        try:
            data = get_crossref_data(doi)
            bibtex = convert_to_bibtex(data)
            ris = convert_to_ris(data)
            
            self.current_bibtex = bibtex
            self.current_ris = ris
            self.current_doi = data.get('DOI', doi)
            self.current_crossref_data = data  # Store for Zotero
            
            self.after(0, self._update_output_display)
            self.after(0, lambda: self.set_status("✓ Successfully converted!", "success"))
            self.after(0, self._check_zotero_status)
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
        
        self.search_button.configure(state="disabled", text="Searching...")
        self.set_status("Searching CrossRef...", "info")
        
        thread = threading.Thread(target=self._perform_search, args=(parsed,))
        thread.start()
    
    def _perform_search(self, parsed: Dict):
        """Perform the CrossRef search in a background thread."""
        try:
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
                self._process_selected_result(results[0])
            else:
                self.after(0, lambda: self._show_search_results(results))
                
        except ValueError as e:
            self.after(0, lambda: self.set_status(f"Error: {e}", "error"))
        except Exception as e:
            self.after(0, lambda: self.set_status(f"Unexpected error: {e}", "error"))
        finally:
            self.after(0, lambda: self.search_button.configure(state="normal", text="Search CrossRef"))
    
    def _process_selected_result(self, data: Dict):
        """Process a selected search result."""
        bibtex = convert_to_bibtex(data)
        ris = convert_to_ris(data)
        
        self.current_bibtex = bibtex
        self.current_ris = ris
        self.current_doi = data.get('DOI')
        self.current_crossref_data = data
        
        self.after(0, self._update_output_display)
        self.after(0, lambda: self.set_status("✓ Found 1 matching reference!", "success"))
        self.after(0, self._check_zotero_status)
    
    def _show_search_results(self, results: List[Dict]):
        """Show the search results in an embedded frame."""
        self.set_status(f"Found {len(results)} matches - please select one", "info")
        
        # Hide the output frame temporarily and show results frame
        self.output_frame.pack_forget()
        
        # Create the results frame
        self.results_frame = SearchResultsFrame(
            self.main_frame, 
            results, 
            callback=self._on_search_result_selected
        )
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    def _on_search_result_selected(self, selected_item):
        """Handle search result selection."""
        # Remove results frame
        if hasattr(self, 'results_frame') and self.results_frame:
            self.results_frame.destroy()
            self.results_frame = None
        
        # Show output frame again
        self.output_frame.pack(fill="x", padx=10, pady=5)
        
        if selected_item:
            bibtex = convert_to_bibtex(selected_item)
            ris = convert_to_ris(selected_item)
            
            self.current_bibtex = bibtex
            self.current_ris = ris
            self.current_doi = selected_item.get('DOI')
            self.current_crossref_data = selected_item
            
            self._update_output_display()
            self.set_status("✓ Successfully converted selected reference!", "success")
            self._check_zotero_status()
        else:
            self.set_status("Selection cancelled", "info")
    
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
        """Copy current output (BibTeX or RIS) to clipboard."""
        if self.format_var.get() == "bibtex":
            text_to_copy = self.current_bibtex
            format_name = "BibTeX"
        else:
            text_to_copy = self.current_ris
            format_name = "RIS"
        
        if text_to_copy:
            if copy_to_clipboard_tk(text_to_copy, self):
                self.set_status(f"✓ Copied {format_name} to clipboard!", "success")
            else:
                self.set_status("⚠ Could not copy to clipboard", "warning")
        else:
            self.set_status("Nothing to copy", "warning")
    
    def download_open_access(self):
        """Try to download open access version via Unpaywall."""
        if not self.current_doi:
            self.set_status("No paper selected - convert a DOI or search first", "warning")
            return
        
        self.oa_button.configure(state="disabled", text="Searching...")
        self.set_status("Searching Unpaywall for open access version...", "info")
        
        # Run in thread to prevent GUI freeze
        thread = threading.Thread(target=self._download_oa_thread)
        thread.start()
    
    def _download_oa_thread(self):
        """Download open access paper in background thread."""
        try:
            result = download_or_open_paper(
                self.current_doi,
                open_pdf=True,
                fallback_browser=False  # Don't fall back - user can use Journal button
            )
            
            if result['success']:
                self.after(0, lambda: self.set_status(f"✓ {result['message']}", "success"))
            elif result.get('pdf_url'):
                # Found URL but couldn't download directly - open it
                if open_url(result['pdf_url']):
                    self.after(0, lambda: self.set_status(f"📄 Opened OA version in browser", "success"))
                else:
                    self.after(0, lambda: self.set_status(f"Found OA at: {result['pdf_url']}", "info"))
            else:
                self.after(0, lambda: self.set_status(
                    "No open access version found. Try '🏛️ Journal' for institutional access.", 
                    "warning"
                ))
        except Exception as e:
            self.after(0, lambda: self.set_status(f"Error: {e}", "error"))
        finally:
            self.after(0, lambda: self.oa_button.configure(state="normal", text="📄 Open Access"))
    
    def open_journal_page(self):
        """Open the journal/publisher page via DOI URL (for institutional access)."""
        if not self.current_doi:
            self.set_status("No paper selected - convert a DOI or search first", "warning")
            return
        
        doi_url = get_doi_url(self.current_doi)
        self.set_status(f"Opening {doi_url}...", "info")
        
        if open_url(doi_url):
            self.set_status(f"🏛️ Opened journal page - use institutional login if needed", "success")
        else:
            self.set_status(f"Couldn't open browser. URL: {doi_url}", "error")
    
    def add_to_zotero(self):
        """Add current reference to Zotero via local connector."""
        if not self.current_crossref_data:
            self.set_status("No reference selected - convert a DOI or search first", "warning")
            return
        
        self.zotero_button.configure(state="disabled", text="Adding...")
        self.set_status("Sending to Zotero...", "info")
        
        # Run in thread to prevent GUI freeze
        thread = threading.Thread(target=self._add_to_zotero_thread)
        thread.start()
    
    def _add_to_zotero_thread(self):
        """Add to Zotero in background thread."""
        try:
            success, message = send_to_zotero_local(self.current_crossref_data)
            
            if success:
                self.after(0, lambda: self.set_status(f"✓ {message}", "success"))
            else:
                self.after(0, lambda: self.set_status(f"⚠ {message}", "warning"))
        except Exception as e:
            self.after(0, lambda: self.set_status(f"Error: {e}", "error"))
        finally:
            self.after(0, lambda: self.zotero_button.configure(state="normal", text="📚 Add to Zotero"))
            self.after(0, self._check_zotero_status)
    
    def clear_all(self):
        self.doi_entry.delete(0, "end")
        self.search_entry.delete("1.0", "end")
        self.output_text.delete("1.0", "end")
        self.parsed_label.configure(text="")
        self.current_bibtex = ""
        self.current_ris = ""
        self.current_doi = None
        self.current_crossref_data = None
        self.set_status("", "info")


def main():
    app = BibTexerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
