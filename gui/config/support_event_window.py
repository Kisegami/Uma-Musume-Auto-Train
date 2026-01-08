"""
Support Card Event Custom Choices Window for Uma Musume Auto-Train Bot GUI

Displays support card events with search, selection, and custom choice management.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import os

try:
    from ..font_manager import get_font
except ImportError:
    from font_manager import get_font


class SupportEventWindow:
    """Window for editing Support Card event choices"""
    
    def __init__(self, parent, colors, template_name, template_path=None):
        """Initialize the Support Card Event Custom Choices Window
        
        Args:
            parent: Parent window
            colors: Color scheme dictionary
            template_name: Name of the template
            template_path: Path to existing template file (None for new)
        """
        self.parent = parent
        self.colors = colors
        self.template_name = template_name
        self.template_path = template_path
        self.custom_choices = []  # List of {EventName, CardSlug, SelectedOption}
        self.all_events = []  # All available events from support_card.json
        self.event_rows = {}  # Track UI rows by unique key
        self.choice_buttons = {}  # Store button references
        self.result_labels = {}  # Store result labels by unique_key and option
        
        # Load all support card events
        self.load_all_events()
        
        # Load existing template if provided
        if template_path and os.path.exists(template_path):
            self.load_template(template_path)
        
        # Create the window
        self.create_window()
    
    def load_all_events(self):
        """Load all events from support_card.json, filtering out events without choices"""
        try:
            with open('assets/events/support_card.json', 'r', encoding='utf-8') as f:
                raw_events = json.load(f)
            
            # Filter out events without choices (events where EventOptions has only empty key)
            self.all_events = []
            for evt in raw_events:
                event_options = evt.get("EventOptions", {})
                # Check if event has meaningful choices (not just empty key)
                has_choices = any(key.strip() for key in event_options.keys())
                if has_choices:
                    self.all_events.append(evt)
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load support card events: {e}")
            self.all_events = []
    
    def load_template(self, filepath):
        """Load existing template from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.custom_choices = data.get("CustomChoices", [])
        except Exception:
            self.custom_choices = []
    
    def create_window(self):
        """Create the window with event search and choices table"""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title(f"Support Card Event Choices - {self.template_name}")
        self.window.geometry("1100x700")
        self.window.configure(fg_color=self.colors['bg_dark'])
        
        try:
            self.window.transient(self.parent)
        except Exception:
            pass
        self.window.lift()
        self.window.focus_force()
        try:
            self.window.attributes("-topmost", True)
            self.window.after(200, lambda: self.window.attributes("-topmost", False))
        except Exception:
            pass
        
        # Title
        title_label = ctk.CTkLabel(
            self.window,
            text=f"Support Card Events - {self.template_name}",
            font=get_font('title_medium'),
            text_color=self.colors['text_light']
        )
        title_label.pack(pady=(15, 10))
        
        # Search frame
        search_frame = ctk.CTkFrame(self.window, fg_color=self.colors['bg_medium'], corner_radius=10)
        search_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        ctk.CTkLabel(
            search_frame,
            text="Add Event:",
            font=get_font('body'),
            text_color=self.colors['text_light']
        ).pack(side=tk.LEFT, padx=(15, 10), pady=10)
        
        # Container frame for search entry and dropdown
        self.search_container = ctk.CTkFrame(search_frame, fg_color="transparent")
        self.search_container.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Search entry with autocomplete
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.search_container,
            textvariable=self.search_var,
            width=400,
            placeholder_text="Type to search events...",
            font=get_font('body')
        )
        self.search_entry.pack()
        self.search_entry.bind('<KeyRelease>', self.on_search_change)
        self.search_entry.bind('<Return>', self.add_from_search)
        self.search_entry.bind('<FocusOut>', self.hide_dropdown_delayed)
        
        # Dropdown frame (initially hidden)
        self.dropdown_frame = None
        
        # Add button
        add_btn = ctk.CTkButton(
            search_frame,
            text="Add",
            command=self.add_from_search,
            fg_color=self.colors['accent_green'],
            corner_radius=8,
            width=80,
            font=get_font('button')
        )
        add_btn.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Create scrollable frame for events
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.window,
            fg_color=self.colors['bg_medium'],
            corner_radius=10
        )
        self.scroll_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Configure grid columns
        self.scroll_frame.grid_columnconfigure(0, weight=1)  # Source (CardSlug)
        self.scroll_frame.grid_columnconfigure(1, weight=2)  # Event name
        self.scroll_frame.grid_columnconfigure(2, weight=1)  # Choices
        self.scroll_frame.grid_columnconfigure(3, weight=3)  # Result
        self.scroll_frame.grid_columnconfigure(4, weight=0)  # Delete button
        
        # Header row
        headers = ["Source", "Event Name", "Choices", "Result", ""]
        for col, header in enumerate(headers):
            header_label = ctk.CTkLabel(
                self.scroll_frame,
                text=header,
                font=get_font('body_bold'),
                text_color=self.colors['text_light']
            )
            header_label.grid(row=0, column=col, padx=10, pady=(10, 5), sticky="w")
        
        # Load existing choices
        self.refresh_event_list()
        
        # Buttons frame
        btn_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Save button
        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save",
            command=self.save_template,
            fg_color=self.colors['accent_green'],
            corner_radius=8,
            font=get_font('button')
        )
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Cancel button
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=self.window.destroy,
            fg_color=self.colors['accent_red'],
            corner_radius=8,
            font=get_font('button')
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))
    
    def hide_dropdown_delayed(self, event=None):
        """Hide dropdown after a small delay to allow click events"""
        self.window.after(200, self.hide_dropdown)
    
    def hide_dropdown(self):
        """Hide the dropdown"""
        if self.dropdown_frame:
            self.dropdown_frame.destroy()
            self.dropdown_frame = None
    
    def on_search_change(self, event=None):
        """Handle search text change - show autocomplete dropdown"""
        search_text = self.search_var.get().lower().strip()
        
        # Remove existing dropdown
        if self.dropdown_frame:
            self.dropdown_frame.destroy()
            self.dropdown_frame = None
        
        if not search_text or len(search_text) < 2:
            return
        
        # Find matching events
        matches = []
        seen = set()
        for evt in self.all_events:
            event_name = evt.get("EventName", "")
            card_slug = evt.get("CardSlug", "")
            unique_key = f"{event_name}|{card_slug}"
            
            # Skip if already in custom choices
            if self.is_event_added(event_name, card_slug):
                continue
            
            if unique_key in seen:
                continue
            
            if search_text in event_name.lower() or search_text in card_slug.lower():
                matches.append((event_name, card_slug))
                seen.add(unique_key)
        
        if not matches:
            return
        
        # Limit matches
        matches = matches[:10]
        
        # Create dropdown using pack below the search entry
        self.dropdown_frame = ctk.CTkFrame(
            self.search_container,
            fg_color=self.colors['bg_light'],
            corner_radius=8,
            width=400
        )
        self.dropdown_frame.pack(fill=tk.X, pady=(2, 0))
        
        for event_name, card_slug in matches:
            display_text = f"{event_name} [{card_slug}]"
            btn = ctk.CTkButton(
                self.dropdown_frame,
                text=display_text,
                anchor="w",
                fg_color="transparent",
                hover_color=self.colors['accent_blue'],
                text_color=self.colors['text_light'],
                font=get_font('body_small'),
                height=28,
                command=lambda en=event_name, cs=card_slug: self.select_from_dropdown(en, cs)
            )
            btn.pack(fill=tk.X, padx=5, pady=2)
    
    def select_from_dropdown(self, event_name, card_slug):
        """Select an event from the dropdown"""
        self.search_var.set(f"{event_name} [{card_slug}]")
        if self.dropdown_frame:
            self.dropdown_frame.destroy()
            self.dropdown_frame = None
    
    def is_event_added(self, event_name, card_slug):
        """Check if an event is already added"""
        for choice in self.custom_choices:
            if choice.get("EventName") == event_name and choice.get("CardSlug") == card_slug:
                return True
        return False
    
    def add_from_search(self, event=None):
        """Add event from search"""
        search_text = self.search_var.get().strip()
        
        # Parse the search text for event name and card slug
        if "[" in search_text and "]" in search_text:
            # Format: "Event Name [card-slug]"
            event_name = search_text[:search_text.rfind("[")].strip()
            card_slug = search_text[search_text.rfind("[")+1:search_text.rfind("]")].strip()
        else:
            # Search for exact match
            event_name = search_text
            card_slug = None
            for evt in self.all_events:
                if evt.get("EventName", "").lower() == search_text.lower():
                    event_name = evt.get("EventName")
                    card_slug = evt.get("CardSlug")
                    break
        
        if not card_slug:
            messagebox.showwarning("Warning", "Please select an event from the dropdown")
            return
        
        # Check for duplicates
        if self.is_event_added(event_name, card_slug):
            # Find and highlight the existing row
            messagebox.showinfo("Info", f"Event '{event_name}' from '{card_slug}' is already added")
            return
        
        # Get all options for this event
        options = self.get_event_options(event_name, card_slug)
        
        # Add to custom choices
        self.custom_choices.append({
            "EventName": event_name,
            "CardSlug": card_slug,
            "SelectedOption": None
        })
        
        # Sort by CardSlug
        self.custom_choices.sort(key=lambda x: x.get("CardSlug", ""))
        
        # Refresh display
        self.refresh_event_list()
        
        # Clear search
        self.search_var.set("")
        if self.dropdown_frame:
            self.dropdown_frame.destroy()
            self.dropdown_frame = None
    
    def get_event_options(self, event_name, card_slug):
        """Get all options for a specific event (only those with non-empty option keys)"""
        options = []
        for evt in self.all_events:
            if evt.get("EventName") == event_name and evt.get("CardSlug") == card_slug:
                event_options = evt.get("EventOptions", {})
                for option_key, result in event_options.items():
                    if option_key.strip():  # Only include options with non-empty keys
                        options.append({
                            "option": option_key,
                            "result": result
                        })
        return options
    
    def refresh_event_list(self):
        """Refresh the event list display"""
        # Clear existing rows (except header)
        for widget in self.scroll_frame.winfo_children():
            info = widget.grid_info()
            if info and int(info.get('row', 0)) > 0:
                widget.destroy()
        
        self.choice_buttons = {}
        self.result_labels = {}
        
        # Create rows for each custom choice
        for idx, choice in enumerate(self.custom_choices):
            self.create_event_row(idx + 1, choice)
    
    def create_event_row(self, row, choice):
        """Create a row for an event"""
        event_name = choice.get("EventName", "")
        card_slug = choice.get("CardSlug", "")
        selected_option = choice.get("SelectedOption")
        unique_key = f"{event_name}|{card_slug}"
        
        # Source (CardSlug)
        source_label = ctk.CTkLabel(
            self.scroll_frame,
            text=card_slug,
            font=get_font('body_small'),
            text_color=self.colors['text_muted'],
            wraplength=150
        )
        source_label.grid(row=row, column=0, padx=10, pady=5, sticky="nw")
        
        # Event name
        name_label = ctk.CTkLabel(
            self.scroll_frame,
            text=event_name,
            font=get_font('body'),
            text_color=self.colors['text_light'],
            wraplength=200,
            justify="left"
        )
        name_label.grid(row=row, column=1, padx=10, pady=5, sticky="nw")
        
        # Get options for this event
        options = self.get_event_options(event_name, card_slug)
        
        # Choices frame
        choices_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        choices_frame.grid(row=row, column=2, padx=10, pady=5, sticky="nw")
        
        # Result label (single label that shows selected result)
        result_label = ctk.CTkLabel(
            self.scroll_frame,
            text="",
            font=get_font('body_small'),
            text_color=self.colors['text_muted'],
            wraplength=300,
            justify="left"
        )
        result_label.grid(row=row, column=3, padx=10, pady=5, sticky="nw")
        self.result_labels[unique_key] = result_label
        
        self.choice_buttons[unique_key] = {}
        
        # Build option result map for this event
        option_results = {opt["option"]: opt["result"] for opt in options}
        
        for opt in options:
            option_name = opt["option"]
            
            # Choice button
            is_selected = selected_option == option_name
            btn = ctk.CTkButton(
                choices_frame,
                text=option_name,
                width=100,
                height=26,
                corner_radius=6,
                fg_color=self.colors['accent_green'] if is_selected else self.colors['bg_light'],
                hover_color=self.colors['accent_blue'],
                font=get_font('body_small'),
                command=lambda uk=unique_key, on=option_name, ores=option_results: self.select_choice(uk, on, ores)
            )
            btn.pack(pady=2)
            self.choice_buttons[unique_key][option_name] = btn
        
        # Show result if option is already selected
        if selected_option and selected_option in option_results:
            result_text = option_results[selected_option]
            result_display = result_text.replace("\\r\\n", "\n").replace("\r\n", "\n")
            result_label.configure(text=result_display)
        
        # Delete button
        del_btn = ctk.CTkButton(
            self.scroll_frame,
            text="✕",
            width=30,
            height=30,
            corner_radius=6,
            fg_color=self.colors['accent_red'],
            font=get_font('body'),
            command=lambda en=event_name, cs=card_slug: self.remove_event(en, cs)
        )
        del_btn.grid(row=row, column=4, padx=10, pady=5, sticky="n")
    
    def select_choice(self, unique_key, option_name, option_results):
        """Select a choice for an event"""
        # Reset all buttons for this event
        for opt, btn in self.choice_buttons[unique_key].items():
            btn.configure(fg_color=self.colors['bg_light'])
        
        # Highlight selected
        self.choice_buttons[unique_key][option_name].configure(
            fg_color=self.colors['accent_green']
        )
        
        # Update result label
        if unique_key in self.result_labels:
            result_text = option_results.get(option_name, "")
            result_display = result_text.replace("\\r\\n", "\n").replace("\r\n", "\n")
            self.result_labels[unique_key].configure(text=result_display)
        
        # Update custom_choices
        event_name, card_slug = unique_key.split("|")
        for choice in self.custom_choices:
            if choice.get("EventName") == event_name and choice.get("CardSlug") == card_slug:
                choice["SelectedOption"] = option_name
                break
    
    def remove_event(self, event_name, card_slug):
        """Remove an event from the list"""
        self.custom_choices = [
            c for c in self.custom_choices
            if not (c.get("EventName") == event_name and c.get("CardSlug") == card_slug)
        ]
        self.refresh_event_list()
    
    def save_template(self):
        """Save template to file"""
        try:
            os.makedirs(os.path.join("template", "events"), exist_ok=True)
            
            # Sanitize template name
            safe_name = self.template_name.replace("/", "-").replace("\\", "-").replace(":", "-")
            filepath = os.path.join("template", "events", f"SupportCards_{safe_name}.json")
            
            data = {
                "TemplateName": self.template_name,
                "CustomChoices": self.custom_choices
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            messagebox.showinfo("Success", f"Template saved to {filepath}")
            self.window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save template: {e}")
