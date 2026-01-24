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
    parse_reference,
    format_search_result_long,
    copy_to_clipboard_tk,
)


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
            formatted = format_search_result_long(item)
            
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
            self.destroy()
    
    def cancel(self):
        """Cancel the dialog."""
        self.selected_item = None
        self.destroy()


class BibTexerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title(f"BibTexer v{__version__} - DOI to BibTeX Converter")
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
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add tabs
        self.tab_doi = self.tabview.add("DOI Lookup")
        self.tab_search = self.tabview.add("Reference Search")
        
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
        search_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
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
            self.current_bibtex = bibtex
            
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
                bibtex = convert_to_bibtex(results[0])
                self.current_bibtex = bibtex
                self.after(0, lambda: self._update_output(bibtex))
                self.after(0, lambda: self.set_status("✓ Found 1 matching reference!", "success"))
            else:
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
            if copy_to_clipboard_tk(self.current_bibtex, self):
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
