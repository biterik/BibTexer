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


class SearchResultsDialog(tk.Toplevel):
    """Dialog to display and select from search results."""
    
    def __init__(self, parent, results: List[Dict], callback):
        super().__init__(parent)
        
        self.results = results
        self.selected_item = None
        self.selected_index = None
        self.callback = callback
        
        # Basic window setup
        self.title("Select Reference")
        self.geometry("900x550")
        self.minsize(700, 400)
        
        # Set background color based on appearance mode
        bg_color = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0"
        self.configure(bg=bg_color)
        
        # Make modal
        self.transient(parent)
        
        # Main container frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text=f"Found {len(results)} matching references",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        instruction_label = ctk.CTkLabel(
            main_frame,
            text="Click to select, then 'Use Selected' or double-click to confirm",
            font=ctk.CTkFont(size=12)
        )
        instruction_label.pack(pady=(0, 10))
        
        # Results list with canvas for scrolling
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Canvas with scrollbars
        canvas_bg = "#333333" if ctk.get_appearance_mode() == "Dark" else "#e8e8e8"
        self.canvas = tk.Canvas(list_frame, highlightthickness=0, bg=canvas_bg)
        
        # Scrollbars
        v_scrollbar = ctk.CTkScrollbar(list_frame, orientation="vertical", command=self.canvas.yview)
        v_scrollbar.pack(side="right", fill="y")
        
        h_scrollbar = ctk.CTkScrollbar(list_frame, orientation="horizontal", command=self.canvas.xview)
        h_scrollbar.pack(side="bottom", fill="x")
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Inner frame for content
        self.inner_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        
        # Create result items with multi-line format
        self.result_frames = []
        for i, item in enumerate(results):
            result_frame = self._create_result_item(i, item)
            self.result_frames.append(result_frame)
        
        # Update scroll region
        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)
        
        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=5, pady=10)
        
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
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # Center and show
        self.after(50, self._finalize_window)
    
    def _create_result_item(self, index: int, item: Dict) -> ctk.CTkFrame:
        """Create a multi-line result item."""
        frame = ctk.CTkFrame(
            self.inner_frame,
            fg_color="transparent",
            corner_radius=5
        )
        frame.pack(fill="x", padx=5, pady=3)
        
        # Extract info
        title = item.get('title', ['No title'])[0] if isinstance(item.get('title'), list) else item.get('title', 'No title')
        
        authors = item.get('author', [])
        if authors:
            author_names = []
            for a in authors[:3]:
                name = f"{a.get('family', '')}, {a.get('given', '')}"
                author_names.append(name.strip(', '))
            author_str = "; ".join(author_names)
            if len(authors) > 3:
                author_str += f" et al. ({len(authors)} authors)"
        else:
            author_str = "Unknown authors"
        
        year = ""
        if 'published-print' in item:
            year = str(item['published-print'].get('date-parts', [['']])[0][0])
        elif 'published-online' in item:
            year = str(item['published-online'].get('date-parts', [['']])[0][0])
        elif 'issued' in item:
            year = str(item['issued'].get('date-parts', [['']])[0][0])
        
        journal = item.get('container-title', [''])[0] if isinstance(item.get('container-title'), list) else item.get('container-title', '')
        doi = item.get('DOI', '')
        
        # Line 1: Title (bold)
        title_label = ctk.CTkLabel(
            frame,
            text=f"{index + 1}. {title}",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            wraplength=800
        )
        title_label.pack(fill="x", padx=10, pady=(5, 0))
        
        # Line 2: Authors
        author_label = ctk.CTkLabel(
            frame,
            text=f"    {author_str}",
            font=ctk.CTkFont(size=11),
            anchor="w",
            text_color=("gray30", "gray70")
        )
        author_label.pack(fill="x", padx=10, pady=0)
        
        # Line 3: Journal, Year, DOI
        meta_parts = []
        if journal:
            meta_parts.append(journal)
        if year:
            meta_parts.append(f"({year})")
        if doi:
            meta_parts.append(f"DOI: {doi}")
        
        meta_label = ctk.CTkLabel(
            frame,
            text=f"    {' • '.join(meta_parts)}",
            font=ctk.CTkFont(size=10),
            anchor="w",
            text_color=("gray40", "gray60")
        )
        meta_label.pack(fill="x", padx=10, pady=(0, 5))
        
        # Make entire frame clickable
        for widget in [frame, title_label, author_label, meta_label]:
            widget.bind("<Button-1>", lambda e, idx=index: self.select_result(idx))
            widget.bind("<Double-Button-1>", lambda e, idx=index: self.confirm_selection(idx))
        
        return frame
    
    def _finalize_window(self):
        """Center and show window."""
        try:
            self.update_idletasks()
            
            # Center on parent
            parent = self.master
            x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
            y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
            x = max(0, x)
            y = max(0, y)
            self.geometry(f"+{x}+{y}")
            
            # Show window
            self.deiconify()
            self.lift()
            self.focus_force()
            
            # Set grab
            self.after(100, self._setup_grab)
        except Exception:
            pass
    
    def _setup_grab(self):
        """Setup modal grab."""
        try:
            self.grab_set()
        except Exception:
            pass
    
    def _on_frame_configure(self, event):
        """Update scroll region."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """Adjust inner frame width."""
        canvas_width = event.width
        frame_width = self.inner_frame.winfo_reqwidth()
        if canvas_width > frame_width:
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def _on_mousewheel(self, event):
        """Vertical scroll."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_shift_mousewheel(self, event):
        """Horizontal scroll."""
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def select_result(self, index: int):
        """Highlight selected result."""
        for i, frame in enumerate(self.result_frames):
            if i == index:
                frame.configure(fg_color=("gray75", "gray35"))
            else:
                frame.configure(fg_color="transparent")
        self.selected_index = index
        self.use_button.configure(state="normal")
    
    def confirm_selection(self, index: int):
        """Confirm on double-click."""
        self.selected_index = index
        self.use_selected()
    
    def use_selected(self):
        """Use selected result."""
        if self.selected_index is not None:
            self.selected_item = self.results[self.selected_index]
            # Unbind events
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Shift-MouseWheel>")
            self.callback(self.selected_item)
            self.destroy()
    
    def cancel(self):
        """Cancel selection."""
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Shift-MouseWheel>")
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
        
        # Output text area - use tk.Text for reliability in bundled apps
        text_bg = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#ffffff"
        text_fg = "#ffffff" if ctk.get_appearance_mode() == "Dark" else "#000000"
        self.output_text = tk.Text(
            self.output_frame, 
            font=("Courier", 12),
            wrap="word",
            height=12,
            bg=text_bg,
            fg=text_fg,
            insertbackground=text_fg
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
        self.update()  # Force full update
    
    def toggle_theme(self):
        if self.theme_switch.get():
            ctk.set_appearance_mode("dark")
            self.output_text.configure(bg="#2b2b2b", fg="#ffffff", insertbackground="#ffffff")
        else:
            ctk.set_appearance_mode("light")
            self.output_text.configure(bg="#ffffff", fg="#000000", insertbackground="#000000")
    
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
            
            # Store data
            self.current_bibtex = bibtex
            self.current_ris = ris
            self.current_doi = data.get('DOI', doi)
            self.current_crossref_data = data
            
            # Schedule UI updates on main thread
            def update_ui():
                self._update_output_display()
                self.set_status("✓ Successfully converted!", "success")
                self._check_zotero_status()
                self.convert_button.configure(state="normal", text="Convert")
            
            self.after(0, update_ui)
            
        except ValueError as e:
            def show_error():
                self.set_status(f"Error: {e}", "error")
                self._update_output("")
                self.convert_button.configure(state="normal", text="Convert")
            self.after(0, show_error)
        except Exception as e:
            def show_error():
                self.set_status(f"Unexpected error: {e}", "error")
                self._update_output("")
                self.convert_button.configure(state="normal", text="Convert")
            self.after(0, show_error)
    
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
        self.update()  # Force UI update
        
        # Perform search directly (no threading) to debug
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
                self.set_status("No results found", "warning")
                self._update_output("")
            elif len(results) == 1:
                self._process_selected_result(results[0])
            else:
                self._show_search_results(results)
                
        except Exception as e:
            self.set_status(f"Error: {e}", "error")
            self._update_output("")
        finally:
            self.search_button.configure(state="normal", text="Search CrossRef")
    
    def _process_selected_result(self, data: Dict):
        """Process a selected search result."""
        bibtex = convert_to_bibtex(data)
        ris = convert_to_ris(data)
        
        self.current_bibtex = bibtex
        self.current_ris = ris
        self.current_doi = data.get('DOI')
        self.current_crossref_data = data
        
        self._update_output_display()
        self.set_status("✓ Found 1 matching reference!", "success")
        self._check_zotero_status()
    
    def _show_search_results(self, results: List[Dict]):
        """Show the search results in a popup dialog."""
        self.set_status(f"Found {len(results)} matches - please select one", "info")
        
        # Create dialog
        dialog = SearchResultsDialog(self, results, callback=self._on_search_result_selected)
    
    def _on_search_result_selected(self, selected_item):
        """Handle search result selection."""
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
        self.output_text.update()  # Force UI update
        self.update_idletasks()  # Process pending events
    
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
