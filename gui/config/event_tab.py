"""
Event Tab for Uma Musume Auto-Train Bot GUI Configuration

Contains event handling settings and choice priorities.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import os
import glob

try:
    from ..font_manager import get_font
except ImportError:
    from font_manager import get_font

try:
    from .uma_event_window import UmaEventWindow
    from .support_event_window import SupportEventWindow
except ImportError:
    from uma_event_window import UmaEventWindow
    from support_event_window import SupportEventWindow


class EventTab:
    """Event configuration tab containing event choice management"""
    
    def __init__(self, tabview, config_panel, colors):
        """Initialize the Event tab
        
        Args:
            tabview: The parent CTkTabview widget
            config_panel: Reference to the main ConfigPanel instance
            colors: Color scheme dictionary
        """
        self.tabview = tabview
        self.config_panel = config_panel
        self.colors = colors
        self.main_window = config_panel.main_window
        
        # Load Uma data for dropdown
        self.uma_data = self.load_uma_data()
        # Sort Uma names A-Z, with "All" at the top
        sorted_uma_names = sorted([uma.get("UmaName", "") for uma in self.uma_data])
        self.uma_names = ["All"] + sorted_uma_names
        
        # Load support card templates
        self.support_templates = self.load_support_templates()
        
        # Create the tab
        self.create_tab()
    
    def load_uma_data(self):
        """Load Uma data from JSON file"""
        try:
            with open('assets/events/uma_data.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def load_support_templates(self):
        """Load available support card templates"""
        templates = []
        if os.path.exists(os.path.join("template", "events")):
            for filepath in glob.glob(os.path.join("template", "events", "SupportCards_*.json")):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        templates.append(data.get("TemplateName", os.path.basename(filepath)))
                except Exception:
                    pass
        return templates
    
    def create_tab(self):
        """Create the Event tab with event choice management"""
        # Add tab to tabview
        event_tab = self.tabview.add("Event")
        
        # Create scrollable frame inside the event tab
        event_scroll = ctk.CTkScrollableFrame(event_tab, fg_color="transparent", corner_radius=0)
        event_scroll.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ==================== Event Choice Management ====================
        event_frame = ctk.CTkFrame(event_scroll, fg_color=self.colors['bg_light'], corner_radius=10)
        event_frame.pack(fill=tk.X, pady=10, padx=10)
        
        event_title = ctk.CTkLabel(event_frame, text="Event Choice Management", font=get_font('section_title'), text_color=self.colors['text_light'])
        event_title.pack(pady=(15, 10))
        
        # Good Choices Section
        good_frame = ctk.CTkFrame(event_frame, fg_color="transparent")
        good_frame.pack(fill=tk.X, padx=15, pady=10)
        
        ctk.CTkLabel(good_frame, text="Good Choices:", text_color=self.colors['text_light'], font=get_font('body_large')).pack(side=tk.LEFT)
        good_btn = ctk.CTkButton(good_frame, text="Open List", 
                                command=self.open_good_choices_window,
                                fg_color=self.colors['accent_green'], corner_radius=8, height=30, width=100,
                                font=get_font('button'))
        good_btn.pack(side=tk.RIGHT)
        
        # Bad Choices Section
        bad_frame = ctk.CTkFrame(event_frame, fg_color="transparent")
        bad_frame.pack(fill=tk.X, padx=15, pady=(10, 15))
        
        ctk.CTkLabel(bad_frame, text="Bad Choices:", text_color=self.colors['text_light'], font=get_font('body_large')).pack(side=tk.LEFT)
        bad_btn = ctk.CTkButton(bad_frame, text="Open List", 
                               command=self.open_bad_choices_window,
                               fg_color=self.colors['accent_red'], corner_radius=8, height=30, width=100,
                               font=get_font('button'))
        bad_btn.pack(side=tk.RIGHT)
        
        # ==================== Uma Events Management ====================
        uma_frame = ctk.CTkFrame(event_scroll, fg_color=self.colors['bg_light'], corner_radius=10)
        uma_frame.pack(fill=tk.X, pady=10, padx=10)
        
        uma_title = ctk.CTkLabel(uma_frame, text="Uma Events Management", font=get_font('section_title'), text_color=self.colors['text_light'])
        uma_title.pack(pady=(15, 10))
        
        # Uma Name dropdown row
        uma_dropdown_frame = ctk.CTkFrame(uma_frame, fg_color="transparent")
        uma_dropdown_frame.pack(fill=tk.X, padx=15, pady=10)
        
        ctk.CTkLabel(uma_dropdown_frame, text="Uma Name:", text_color=self.colors['text_light'], font=get_font('body_large')).pack(side=tk.LEFT)
        
        # Use ttk.Combobox for mouse wheel scroll support
        from tkinter import ttk
        
        # Style the combobox to match dark theme
        style = ttk.Style()
        style.configure("Uma.TCombobox", 
                       fieldbackground=self.colors['bg_light'],
                       background=self.colors['bg_light'],
                       foreground=self.colors['text_light'])
        
        self.uma_var = tk.StringVar(value="All")
        self.uma_combobox = ttk.Combobox(
            uma_dropdown_frame,
            textvariable=self.uma_var,
            values=self.uma_names,
            width=35,
            font=get_font('body'),
            style="Uma.TCombobox"
        )
        self.uma_combobox.pack(side=tk.LEFT, padx=(10, 0))
        self.uma_combobox.bind('<KeyRelease>', self.filter_uma_dropdown)
        
        # Edit Custom Choices button
        uma_edit_btn = ctk.CTkButton(
            uma_dropdown_frame,
            text="Edit Custom Choices",
            command=self.open_uma_event_window,
            fg_color=self.colors['accent_blue'],
            corner_radius=8,
            height=30,
            font=get_font('button')
        )
        uma_edit_btn.pack(side=tk.RIGHT)
        
        # Info label
        uma_info = ctk.CTkLabel(
            uma_frame,
            text="Select a specific Uma to edit their event choices. 'All' cannot be edited.",
            text_color=self.colors['text_muted'],
            font=get_font('body_small')
        )
        uma_info.pack(pady=(0, 15))
        
        # ==================== Support Cards Event Management ====================
        support_frame = ctk.CTkFrame(event_scroll, fg_color=self.colors['bg_light'], corner_radius=10)
        support_frame.pack(fill=tk.X, pady=10, padx=10)
        
        support_title = ctk.CTkLabel(support_frame, text="Support Cards Event Management", font=get_font('section_title'), text_color=self.colors['text_light'])
        support_title.pack(pady=(15, 10))
        
        # Template dropdown row
        template_dropdown_frame = ctk.CTkFrame(support_frame, fg_color="transparent")
        template_dropdown_frame.pack(fill=tk.X, padx=15, pady=10)
        
        ctk.CTkLabel(template_dropdown_frame, text="Template:", text_color=self.colors['text_light'], font=get_font('body_large')).pack(side=tk.LEFT)
        
        self.template_var = tk.StringVar(value=self.support_templates[0] if self.support_templates else "")
        self.template_dropdown = ctk.CTkComboBox(
            template_dropdown_frame,
            values=self.support_templates if self.support_templates else ["(No templates)"],
            variable=self.template_var,
            width=250,
            font=get_font('body'),
            dropdown_font=get_font('body')
        )
        self.template_dropdown.pack(side=tk.LEFT, padx=(10, 0))
        
        # Buttons frame
        support_btn_frame = ctk.CTkFrame(support_frame, fg_color="transparent")
        support_btn_frame.pack(fill=tk.X, padx=15, pady=(5, 15))
        
        # Add New button
        add_template_btn = ctk.CTkButton(
            support_btn_frame,
            text="Add New",
            command=self.add_new_template,
            fg_color=self.colors['accent_green'],
            corner_radius=8,
            height=30,
            width=90,
            font=get_font('button')
        )
        add_template_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Delete button
        delete_template_btn = ctk.CTkButton(
            support_btn_frame,
            text="Delete",
            command=self.delete_template,
            fg_color=self.colors['accent_red'],
            corner_radius=8,
            height=30,
            width=80,
            font=get_font('button')
        )
        delete_template_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Edit Custom Choices button
        support_edit_btn = ctk.CTkButton(
            support_btn_frame,
            text="Edit Custom Choices",
            command=self.open_support_event_window,
            fg_color=self.colors['accent_blue'],
            corner_radius=8,
            height=30,
            font=get_font('button')
        )
        support_edit_btn.pack(side=tk.RIGHT)
    
    def filter_uma_dropdown(self, event=None):
        """Filter Uma dropdown based on typed text"""
        typed = self.uma_var.get().lower()
        if not typed:
            self.uma_combobox['values'] = self.uma_names
            return
        
        filtered = [name for name in self.uma_names if typed in name.lower()]
        if filtered:
            self.uma_combobox['values'] = filtered
    
    def open_uma_event_window(self):
        """Open Uma Event Custom Choices Window"""
        selected_uma = self.uma_var.get()
        
        if selected_uma == "All":
            messagebox.showwarning("Warning", "Please select a specific Uma to edit their event choices.")
            return
        
        # Find the Uma data
        uma_info = None
        for uma in self.uma_data:
            if uma.get("UmaName") == selected_uma:
                uma_info = uma
                break
        
        if not uma_info:
            messagebox.showerror("Error", f"Could not find data for Uma: {selected_uma}")
            return
        
        # Open window
        UmaEventWindow(
            parent=self.config_panel.winfo_toplevel(),
            colors=self.colors,
            uma_name=uma_info.get("UmaName", ""),
            uma_slug=uma_info.get("UmaSlug", ""),
            uma_events=uma_info.get("UmaEvents", [])
        )
    
    def add_new_template(self):
        """Create a new support card template"""
        dialog = ctk.CTkInputDialog(text="Enter template name:", title="New Template")
        template_name = dialog.get_input()
        
        if template_name and template_name.strip():
            template_name = template_name.strip()
            
            # Check for duplicates
            if template_name in self.support_templates:
                messagebox.showwarning("Warning", f"Template '{template_name}' already exists.")
                return
            
            # Open window for new template
            SupportEventWindow(
                parent=self.config_panel.winfo_toplevel(),
                colors=self.colors,
                template_name=template_name
            )
            
            # Refresh templates after window closes
            self.config_panel.winfo_toplevel().after(500, self.refresh_templates)
    
    def delete_template(self):
        """Delete the selected template"""
        selected = self.template_var.get()
        
        if not selected or selected == "(No templates)":
            messagebox.showwarning("Warning", "No template selected.")
            return
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete template '{selected}'?"):
            # Sanitize name
            safe_name = selected.replace("/", "-").replace("\\", "-").replace(":", "-")
            filepath = os.path.join("template", "events", f"SupportCards_{safe_name}.json")
            
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    messagebox.showinfo("Success", f"Template '{selected}' deleted.")
                    self.refresh_templates()
                else:
                    messagebox.showerror("Error", f"Template file not found: {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete template: {e}")
    
    def open_support_event_window(self):
        """Open Support Card Event Custom Choices Window"""
        selected = self.template_var.get()
        
        if not selected or selected == "(No templates)":
            messagebox.showwarning("Warning", "Please select a template or create a new one.")
            return
        
        # Find template file
        safe_name = selected.replace("/", "-").replace("\\", "-").replace(":", "-")
        filepath = os.path.join("Events", f"SupportCards_{safe_name}.json")
        
        SupportEventWindow(
            parent=self.config_panel.winfo_toplevel(),
            colors=self.colors,
            template_name=selected,
            template_path=filepath if os.path.exists(filepath) else None
        )
        
        # Refresh after close
        self.config_panel.winfo_toplevel().after(500, self.refresh_templates)
    
    def refresh_templates(self):
        """Refresh the template dropdown"""
        self.support_templates = self.load_support_templates()
        if self.support_templates:
            self.template_dropdown.configure(values=self.support_templates)
            if self.template_var.get() not in self.support_templates:
                self.template_var.set(self.support_templates[0])
        else:
            self.template_dropdown.configure(values=["(No templates)"])
            self.template_var.set("(No templates)")
    
    def open_good_choices_window(self):
        """Open window to edit good choices list"""
        self.open_event_choices_window("Good_choices", "Good Choices")
    
    def open_bad_choices_window(self):
        """Open window to edit bad choices list"""
        self.open_event_choices_window("Bad_choices", "Bad Choices")
    
    def open_event_choices_window(self, choice_type, title):
        """Open window to edit event choices"""
        try:
            # Load current event priority data
            with open('event_priority.json', 'r', encoding='utf-8') as f:
                event_data = json.load(f)
            
            choices = event_data.get(choice_type, [])
            
            # Create new window
            window = ctk.CTkToplevel(self.config_panel.winfo_toplevel())
            window.title(f"Edit {title}")
            window.geometry("500x400")
            window.configure(fg_color=self.colors['bg_dark'])
            try:
                window.transient(self.config_panel.winfo_toplevel())
            except Exception:
                pass
            window.lift()
            window.focus_force()
            try:
                window.attributes("-topmost", True)
                window.after(200, lambda: window.attributes("-topmost", False))
            except Exception:
                pass
            
            # Title
            title_label = ctk.CTkLabel(window, text=f"Edit {title}", font=get_font('title_medium'), text_color=self.colors['text_light'])
            title_label.pack(pady=(15, 10))
            
            # List frame
            list_frame = ctk.CTkFrame(window, fg_color=self.colors['bg_medium'], corner_radius=10)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
            
            # Choices listbox
            choices_listbox = tk.Listbox(list_frame, bg=self.colors['bg_light'], fg=self.colors['text_light'], 
                                       selectmode=tk.SINGLE, font=get_font('body_large'))
            choices_listbox.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
            
            # Populate listbox
            for choice in choices:
                choices_listbox.insert(tk.END, choice)
            
            # Buttons frame
            btn_frame = ctk.CTkFrame(window, fg_color="transparent")
            btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
            
            # Add button
            add_btn = ctk.CTkButton(btn_frame, text="Add", command=lambda: self.add_event_choice(choices_listbox, choices),
                                  fg_color=self.colors['accent_green'], corner_radius=8)
            add_btn.pack(side=tk.LEFT, padx=(0, 5))
            
            # Remove button
            remove_btn = ctk.CTkButton(btn_frame, text="Remove", command=lambda: self.remove_event_choice(choices_listbox, choices),
                                     fg_color=self.colors['accent_red'], corner_radius=8)
            remove_btn.pack(side=tk.LEFT, padx=(0, 5))
            
            # Move up button
            up_btn = ctk.CTkButton(btn_frame, text="↑", command=lambda: self.move_event_choice(choices_listbox, choices, -1),
                                 fg_color=self.colors['accent_blue'], corner_radius=8, width=40)
            up_btn.pack(side=tk.LEFT, padx=(0, 5))
            
            # Move down button
            down_btn = ctk.CTkButton(btn_frame, text="↓", command=lambda: self.move_event_choice(choices_listbox, choices, 1),
                                   fg_color=self.colors['accent_blue'], corner_radius=8, width=40)
            down_btn.pack(side=tk.LEFT, padx=(0, 5))
            
            # Save button
            save_btn = ctk.CTkButton(btn_frame, text="Save", command=lambda: self.save_event_choices(window, choice_type, choices),
                                   fg_color=self.colors['accent_green'], corner_radius=8)
            save_btn.pack(side=tk.RIGHT)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open {title} window: {e}")
    
    def add_event_choice(self, listbox, choices):
        """Add a new event choice"""
        dialog = ctk.CTkInputDialog(text="Enter new choice:", title="Add Choice")
        choice = dialog.get_input()
        if choice and choice.strip():
            choices.append(choice.strip())
            listbox.insert(tk.END, choice.strip())
    
    def remove_event_choice(self, listbox, choices):
        """Remove selected event choice"""
        selection = listbox.curselection()
        if selection:
            index = selection[0]
            choices.pop(index)
            listbox.delete(index)
    
    def move_event_choice(self, listbox, choices, direction):
        """Move event choice up or down"""
        selection = listbox.curselection()
        if selection:
            index = selection[0]
            new_index = index + direction
            if 0 <= new_index < len(choices):
                choices[index], choices[new_index] = choices[new_index], choices[index]
                # Refresh listbox
                listbox.delete(0, tk.END)
                for choice in choices:
                    listbox.insert(tk.END, choice)
                listbox.selection_set(new_index)
    
    def save_event_choices(self, window, choice_type, choices):
        """Save event choices to file"""
        try:
            with open('event_priority.json', 'r', encoding='utf-8') as f:
                event_data = json.load(f)
            
            event_data[choice_type] = choices
            
            with open('event_priority.json', 'w', encoding='utf-8') as f:
                json.dump(event_data, f, indent=4, ensure_ascii=False)
            
            messagebox.showinfo("Success", f"{choice_type} saved successfully!")
            window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save {choice_type}: {e}")