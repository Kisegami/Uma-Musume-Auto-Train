"""
Uma Event Custom Choices Window for Uma Musume Auto-Train Bot GUI

Displays Uma events in a table-like layout with choice buttons.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os

try:
    from ..font_manager import get_font
except ImportError:
    from font_manager import get_font


class UmaEventWindow:
    """Window for editing Uma-specific event choices"""
    
    def __init__(self, parent, colors, uma_name, uma_slug, uma_events):
        """Initialize the Uma Event Custom Choices Window
        
        Args:
            parent: Parent window
            colors: Color scheme dictionary
            uma_name: Name of the selected Uma
            uma_slug: Slug identifier for the Uma
            uma_events: List of events for this Uma
        """
        self.parent = parent
        self.colors = colors
        self.uma_name = uma_name
        self.uma_slug = uma_slug
        self.uma_events = uma_events
        self.custom_choices = {}
        self.choice_buttons = {}  # Store button references for highlighting
        self.result_labels = {}  # Store result labels by event name
        
        # Load existing choices if available
        self.load_existing_choices()
        
        # Create the window
        self.create_window()
    
    def load_existing_choices(self):
        """Load existing custom choices from file"""
        # Sanitize uma_name for filename
        safe_name = self.uma_name.replace("/", "-").replace("\\", "-").replace(":", "-")
        filepath = os.path.join("template", "events", f"Events_{safe_name}.json")
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.custom_choices = data.get("CustomChoices", {})
            except Exception:
                self.custom_choices = {}
    
    def create_window(self):
        """Create the window with event choices table"""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title(f"Uma Event Choices - {self.uma_name}")
        self.window.geometry("900x600")
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
            text=f"Custom Choices for {self.uma_name}",
            font=get_font('title_medium'),
            text_color=self.colors['text_light']
        )
        title_label.pack(pady=(15, 10))
        
        # Info label
        info_label = ctk.CTkLabel(
            self.window,
            text="Click on a choice button to select it. Selected choices will be highlighted.",
            font=get_font('body'),
            text_color=self.colors['text_muted']
        )
        info_label.pack(pady=(0, 10))
        
        # Create scrollable frame for events
        scroll_frame = ctk.CTkScrollableFrame(
            self.window,
            fg_color=self.colors['bg_medium'],
            corner_radius=10
        )
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Configure grid columns
        scroll_frame.grid_columnconfigure(0, weight=2)  # Event name
        scroll_frame.grid_columnconfigure(1, weight=1)  # Choices
        scroll_frame.grid_columnconfigure(2, weight=3)  # Result
        
        # Header row - use text_light for light color
        headers = ["Event Name", "Choices", "Result"]
        for col, header in enumerate(headers):
            header_label = ctk.CTkLabel(
                scroll_frame,
                text=header,
                font=get_font('body_bold'),
                text_color=self.colors['text_light']
            )
            header_label.grid(row=0, column=col, padx=10, pady=(10, 5), sticky="w")
        
        # Group events by name to combine options, filter out events without choices
        events_grouped = {}
        for event in self.uma_events:
            event_name = event.get("EventName", "Unknown")
            if event_name not in events_grouped:
                events_grouped[event_name] = []
            
            # Extract option info
            event_options = event.get("EventOptions", {})
            for option_key, result in event_options.items():
                if option_key.strip():  # Only include options with non-empty keys
                    events_grouped[event_name].append({
                        "option": option_key,
                        "result": result
                    })
        
        # Filter out events without choices
        events_grouped = {k: v for k, v in events_grouped.items() if v}
        
        # Create rows for each event
        row_idx = 1
        for event_name, options in events_grouped.items():
            self.create_event_row(scroll_frame, row_idx, event_name, options)
            row_idx += 1
        
        # Buttons frame
        btn_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Save button
        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save",
            command=self.save_choices,
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
        
        # Clear all button
        clear_btn = ctk.CTkButton(
            btn_frame,
            text="Clear All",
            command=self.clear_all_choices,
            fg_color=self.colors['bg_light'],
            corner_radius=8,
            font=get_font('button')
        )
        clear_btn.pack(side=tk.LEFT)
    
    def create_event_row(self, parent, row, event_name, options):
        """Create a row for an event with choice buttons
        
        Args:
            parent: Parent widget
            row: Row index
            event_name: Name of the event
            options: List of option dictionaries with 'option' and 'result' keys
        """
        # Event name label
        name_label = ctk.CTkLabel(
            parent,
            text=event_name,
            font=get_font('body'),
            text_color=self.colors['text_light'],
            wraplength=250,
            justify="left"
        )
        name_label.grid(row=row, column=0, padx=10, pady=5, sticky="nw")
        
        # Choices frame (vertical buttons)
        choices_frame = ctk.CTkFrame(parent, fg_color="transparent")
        choices_frame.grid(row=row, column=1, padx=10, pady=5, sticky="nw")
        
        # Result label (single label that updates when choice is selected)
        result_label = ctk.CTkLabel(
            parent,
            text="",
            font=get_font('body_small'),
            text_color=self.colors['text_muted'],
            wraplength=350,
            justify="left"
        )
        result_label.grid(row=row, column=2, padx=10, pady=5, sticky="nw")
        self.result_labels[event_name] = result_label
        
        # Initialize button storage for this event
        self.choice_buttons[event_name] = {}
        
        # Build option result map
        option_results = {opt["option"]: opt["result"] for opt in options}
        
        # Create button for each option
        for i, opt in enumerate(options):
            option_name = opt["option"]
            
            # Create choice button
            btn = ctk.CTkButton(
                choices_frame,
                text=option_name,
                width=120,
                height=28,
                corner_radius=6,
                fg_color=self.colors['bg_light'],
                hover_color=self.colors['accent_blue'],
                font=get_font('body_small'),
                command=lambda en=event_name, on=option_name, ores=option_results: self.select_choice(en, on, ores)
            )
            btn.pack(pady=2)
            self.choice_buttons[event_name][option_name] = btn
        
        # Highlight existing selection and show result
        if event_name in self.custom_choices:
            selected = self.custom_choices[event_name]
            if selected in self.choice_buttons[event_name]:
                self.choice_buttons[event_name][selected].configure(
                    fg_color=self.colors['accent_green']
                )
                # Show the result for this selection
                if selected in option_results:
                    result_text = option_results[selected]
                    result_display = result_text.replace("\\r\\n", "\n").replace("\r\n", "\n")
                    result_label.configure(text=result_display)
    
    def select_choice(self, event_name, option_name, option_results):
        """Select a choice for an event
        
        Args:
            event_name: Name of the event
            option_name: Selected option
            option_results: Dict mapping option names to result text
        """
        # Reset all buttons for this event
        for opt, btn in self.choice_buttons[event_name].items():
            btn.configure(fg_color=self.colors['bg_light'])
        
        # Highlight selected button
        self.choice_buttons[event_name][option_name].configure(
            fg_color=self.colors['accent_green']
        )
        
        # Update result label
        if event_name in self.result_labels:
            result_text = option_results.get(option_name, "")
            result_display = result_text.replace("\\r\\n", "\n").replace("\r\n", "\n")
            self.result_labels[event_name].configure(text=result_display)
        
        # Store selection
        self.custom_choices[event_name] = option_name
    
    def clear_all_choices(self):
        """Clear all selections"""
        for event_name, buttons in self.choice_buttons.items():
            for btn in buttons.values():
                btn.configure(fg_color=self.colors['bg_light'])
        
        # Clear result labels
        for label in self.result_labels.values():
            label.configure(text="")
        
        self.custom_choices = {}
    
    def save_choices(self):
        """Save custom choices to file"""
        try:
            # Ensure template/events directory exists
            os.makedirs(os.path.join("template", "events"), exist_ok=True)
            
            # Sanitize uma_name for filename
            safe_name = self.uma_name.replace("/", "-").replace("\\", "-").replace(":", "-")
            filepath = os.path.join("template", "events", f"Events_{safe_name}.json")
            
            data = {
                "UmaName": self.uma_name,
                "UmaSlug": self.uma_slug,
                "CustomChoices": self.custom_choices
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            messagebox.showinfo("Success", f"Choices saved to {filepath}")
            self.window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save choices: {e}")
