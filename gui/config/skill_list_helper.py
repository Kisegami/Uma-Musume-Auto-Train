"""
Helper functions for skill list management in the Skill Tab
Reworked version with autocomplete, drag & drop, and rarity-based styling
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os
import re

try:
    from ..font_manager import get_font, get_font_tuple
except ImportError:
    from font_manager import get_font, get_font_tuple

# Global skills data cache
_skills_cache = None
_skills_by_name = {}
_skill_rarity_map = {}

def load_skills_data():
    """Load skills data from assets/skills/skills.json and build lookup maps"""
    global _skills_cache, _skills_by_name, _skill_rarity_map
    
    if _skills_cache is not None:
        return _skills_cache
    
    try:
        skills_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'skills', 'skills.json')
        skills_path = os.path.normpath(skills_path)
        
        with open(skills_path, 'r', encoding='utf-8') as f:
            _skills_cache = json.load(f)
        
        # Build name lookup and rarity map
        for rarity in ['Normal', 'Rare', 'Unique']:
            for skill in _skills_cache.get(rarity, []):
                name = skill.get('name', '')
                _skills_by_name[name] = skill
                _skill_rarity_map[name] = rarity
        
        return _skills_cache
    except Exception as e:
        print(f"Error loading skills data: {e}")
        return {'Normal': [], 'Rare': [], 'Unique': []}

def get_skill_rarity(skill_name):
    """Get the rarity of a skill by name"""
    load_skills_data()
    return _skill_rarity_map.get(skill_name, 'Normal')

def get_skill_other_version(skill_name):
    """Get the other_version (normal/child version) of a rare skill"""
    load_skills_data()
    skill = _skills_by_name.get(skill_name, {})
    return skill.get('other_version', None)

def get_all_skill_names():
    """Get all skill names for autocomplete"""
    load_skills_data()
    return list(_skills_by_name.keys())

def get_skill_variants(base_skill_name):
    """Get all variants of a skill (with ×, ◎, ○ suffixes)"""
    # Remove existing suffix if any
    base = re.sub(r'\s*[×◎○]$', '', base_skill_name).strip()
    variants = [
        base,
        f"{base} ×",
        f"{base} ◎", 
        f"{base} ○"
    ]
    return variants


class SkillRowWidget(ctk.CTkFrame):
    """A single skill row with drag handle, skill name, and rarity-based styling"""
    
    def __init__(self, parent, skill_name, colors, on_delete, on_move, on_toggle_child, index, child_skill=None):
        super().__init__(parent, height=40, corner_radius=8)
        self.skill_name = skill_name
        self.colors = colors
        self.on_delete = on_delete
        self.on_move = on_move
        self.on_toggle_child = on_toggle_child
        self.index = index
        self.child_skill = child_skill  # The child skill name if activated
        
        rarity = get_skill_rarity(skill_name)
        self.rarity = rarity
        self.other_version = get_skill_other_version(skill_name) if rarity == 'Rare' else None
        
        # Set background color based on rarity
        if rarity == 'Unique':
            # Pastel purple - no gradient needed
            self.configure(fg_color='#DDD6FE')  # Light pastel purple
            self._is_gradient = False
        elif rarity == 'Rare':
            self.configure(fg_color='#FEF3C7')  # Light pastel yellow
            self._is_gradient = False
        else:
            self.configure(fg_color=colors['bg_light'])
            self._is_gradient = False
        
        self.pack(fill=tk.X, pady=2, padx=5)
        self._create_widgets()
        self._setup_drag_and_drop()
    

    def _create_widgets(self):
        """Create the row widgets"""
        # Up/Down move buttons (cleaner than drag & drop)
        move_frame = ctk.CTkFrame(self, fg_color='transparent', width=50)
        move_frame.pack(side=tk.LEFT, padx=(6, 2))
        
        self.up_btn = ctk.CTkButton(move_frame, text="▲", width=22, height=18,
                                    fg_color=self.colors['accent_blue'],
                                    hover_color='#1E40AF',
                                    font=('Segoe UI', 9),
                                    command=lambda: self.on_move(self, -1))
        self.up_btn.pack(side=tk.TOP)
        
        self.down_btn = ctk.CTkButton(move_frame, text="▼", width=22, height=18,
                                      fg_color=self.colors['accent_blue'],
                                      hover_color='#1E40AF',
                                      font=('Segoe UI', 9),
                                      command=lambda: self.on_move(self, 1))
        self.down_btn.pack(side=tk.TOP)
        
        # Priority number
        self.priority_label = ctk.CTkLabel(self, text=f"{self.index + 1}.", width=30,
                                           text_color='#374151' if self.rarity in ['Rare', 'Unique'] else self.colors['text_light'],
                                           font=get_font('body_medium'))
        self.priority_label.pack(side=tk.LEFT, padx=(2, 5))
        
        # For Rare skills, add arrow button to toggle child skill display
        if self.rarity == 'Rare' and self.other_version:
            self.toggle_child_btn = ctk.CTkButton(
                self, text="←", width=30, height=28,
                fg_color='#B8860B', hover_color='#8B6914',
                font=get_font('body_large'),
                command=self._toggle_child
            )
            self.toggle_child_btn.pack(side=tk.LEFT, padx=(0, 5))
            # Tooltip
            self._create_tooltip(self.toggle_child_btn, f"Add child skill: {self.other_version}")
        
        # Skill name label (will show "RareSkill <- ChildSkill" when child is active)
        text_color = '#374151' if self.rarity in ['Rare', 'Unique'] else self.colors['text_light']
        display_text = self._get_display_text()
        self.name_label = ctk.CTkLabel(self, text=display_text,
                                       text_color=text_color,
                                       font=get_font('body_medium'),
                                       anchor='w')
        self.name_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Show rarity badge
        badge_colors = {'Normal': '#6B7280', 'Rare': '#854D0E', 'Unique': '#5B21B6'}
        self.rarity_badge = ctk.CTkLabel(self, text=self.rarity[0], width=24, height=24,
                                         fg_color=badge_colors.get(self.rarity, '#6B7280'),
                                         corner_radius=12,
                                         text_color='white',
                                         font=get_font('body_small'))
        self.rarity_badge.pack(side=tk.RIGHT, padx=(5, 5))
        
        # Delete button
        self.delete_btn = ctk.CTkButton(self, text="×", width=30, height=28,
                                        fg_color=self.colors['accent_red'],
                                        hover_color='#DC2626',
                                        font=get_font('body_large'),
                                        command=lambda: self.on_delete(self))
        self.delete_btn.pack(side=tk.RIGHT, padx=(5, 8))
    
    def _get_display_text(self):
        """Get the display text for the skill name"""
        if self.child_skill:
            return f"{self.skill_name} ← {self.child_skill}"
        return self.skill_name
    
    def _toggle_child(self):
        """Toggle the child skill display"""
        if self.child_skill:
            # Remove child
            self.child_skill = None
        else:
            # Add child
            self.child_skill = self.other_version
        
        # Update display
        self.name_label.configure(text=self._get_display_text())
        
        # Notify parent to remove variants of child skill from list
        if self.child_skill and self.on_toggle_child:
            self.on_toggle_child(self, self.child_skill)
    
    def set_child_skill(self, child_name):
        """Set the child skill (used when loading from file)"""
        self.child_skill = child_name
        self.name_label.configure(text=self._get_display_text())
    
    def _create_tooltip(self, widget, text):
        """Create a simple tooltip for a widget"""
        tooltip = None
        
        def show_tooltip(event):
            nonlocal tooltip
            x, y = widget.winfo_rootx() + 30, widget.winfo_rooty() + 30
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            label = tk.Label(tooltip, text=text, background="#333", foreground="white",
                           relief='solid', borderwidth=1, font=('Segoe UI', 9), padx=5, pady=2)
            label.pack()
        
        def hide_tooltip(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None
        
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)
    
    def _setup_drag_and_drop(self):
        """Setup move buttons instead of complex drag & drop"""
        pass  # Using buttons instead
    
    def update_index(self, new_index):
        """Update the priority number display"""
        self.index = new_index
        self.priority_label.configure(text=f"{new_index + 1}.")


class SkillAutocompleteEntry(ctk.CTkFrame):
    """Entry with autocomplete dropdown for skill names"""
    
    def __init__(self, parent, colors, on_select):
        super().__init__(parent, fg_color='transparent')
        self.colors = colors
        self.on_select = on_select
        self.all_skills = get_all_skill_names()
        
        self.entry_var = tk.StringVar()
        self.entry = ctk.CTkEntry(self, textvariable=self.entry_var, 
                                  placeholder_text="Type skill name...",
                                  width=400, height=35,
                                  corner_radius=8,
                                  font=get_font('input'))
        self.entry.pack(side=tk.LEFT, padx=(0, 10))
        
        self.add_btn = ctk.CTkButton(self, text="+ Add Skill", width=100, height=35,
                                     fg_color=colors['accent_green'],
                                     hover_color='#059669',
                                     font=get_font('button'),
                                     command=self._on_add_click)
        self.add_btn.pack(side=tk.LEFT)
        
        self.dropdown_frame = None
        self.dropdown_listbox = None
        
        self.entry_var.trace('w', self._on_entry_change)
        self.entry.bind('<Return>', lambda e: self._on_add_click())
        self.entry.bind('<Down>', self._on_arrow_down)
        self.entry.bind('<Escape>', self._hide_dropdown)
    
    def _on_entry_change(self, *args):
        query = self.entry_var.get().lower().strip()
        if len(query) < 1:
            self._hide_dropdown()
            return
        
        matches = [s for s in self.all_skills if query in s.lower()][:15]
        
        if matches:
            self._show_dropdown(matches)
        else:
            self._hide_dropdown()
    
    def _show_dropdown(self, matches):
        self._hide_dropdown()
        
        self.dropdown_frame = tk.Toplevel(self)
        self.dropdown_frame.wm_overrideredirect(True)
        
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        self.dropdown_frame.wm_geometry(f"400x200+{x}+{y}")
        
        frame = tk.Frame(self.dropdown_frame, bg=self.colors['bg_light'])
        frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.dropdown_listbox = tk.Listbox(frame, 
                                           bg=self.colors['bg_light'],
                                           fg=self.colors['text_light'],
                                           selectbackground=self.colors['accent_blue'],
                                           font=get_font_tuple('body_medium'),
                                           yscrollcommand=scrollbar.set,
                                           borderwidth=1,
                                           relief='solid')
        self.dropdown_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.dropdown_listbox.yview)
        
        for skill in matches:
            rarity = get_skill_rarity(skill)
            prefix = {'Normal': '○', 'Rare': '★', 'Unique': '◆'}.get(rarity, '○')
            self.dropdown_listbox.insert(tk.END, f"{prefix} {skill}")
        
        self.dropdown_listbox.bind('<Double-1>', self._on_dropdown_select)
        self.dropdown_listbox.bind('<Return>', self._on_dropdown_select)
        self.dropdown_frame.bind('<FocusOut>', lambda e: self._hide_dropdown())
    
    def _hide_dropdown(self, event=None):
        if self.dropdown_frame:
            try:
                self.dropdown_frame.destroy()
            except:
                pass
            self.dropdown_frame = None
            self.dropdown_listbox = None
    
    def _on_dropdown_select(self, event):
        if self.dropdown_listbox:
            selection = self.dropdown_listbox.curselection()
            if selection:
                item = self.dropdown_listbox.get(selection[0])
                skill_name = item[2:].strip()
                self.entry_var.set(skill_name)
                self._hide_dropdown()
                self._on_add_click()
    
    def _on_arrow_down(self, event):
        if self.dropdown_listbox:
            self.dropdown_listbox.focus_set()
            self.dropdown_listbox.selection_set(0)
    
    def _on_add_click(self):
        skill_name = self.entry_var.get().strip()
        if skill_name:
            self._hide_dropdown()
            self.on_select(skill_name)
            self.entry_var.set('')


def open_skill_list_window(skill_tab_instance):
    """Open window to edit skill lists with new UI"""
    try:
        load_skills_data()
        
        skill_file = skill_tab_instance.get_skill_file_path()
        current_skills = []
        gold_upgrades = {}
        
        if skill_file and os.path.exists(skill_file):
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    current_skills = data.get('skill_priority', [])
                    gold_upgrades = data.get('gold_skill_upgrades', {})
            except:
                pass
        
        colors = skill_tab_instance.colors
        
        window = ctk.CTkToplevel(skill_tab_instance.config_panel.winfo_toplevel())
        window.title("Edit Skill Priority List")
        window.geometry("750x600")
        window.configure(fg_color=colors['bg_dark'])
        window.transient(skill_tab_instance.config_panel.winfo_toplevel())
        window.lift()
        window.focus_force()
        
        # Title
        title_frame = ctk.CTkFrame(window, fg_color='transparent')
        title_frame.pack(fill=tk.X, padx=20, pady=(15, 5))
        
        ctk.CTkLabel(title_frame, text="Skill Priority List", 
                    font=get_font('title_medium'),
                    text_color=colors['text_light']).pack(side=tk.LEFT)
        
        # Legend
        legend_frame = ctk.CTkFrame(title_frame, fg_color='transparent')
        legend_frame.pack(side=tk.RIGHT)
        ctk.CTkLabel(legend_frame, text="○ Normal", text_color='#9CA3AF', 
                    font=get_font('body_small')).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(legend_frame, text="★ Rare (← toggle child)", text_color='#D4A017', 
                    font=get_font('body_small')).pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(legend_frame, text="◆ Unique", text_color='#8B5CF6', 
                    font=get_font('body_small')).pack(side=tk.LEFT, padx=5)
        
        skill_rows = []
        
        def refresh_indices():
            for i, row in enumerate(skill_rows):
                row.update_index(i)
        
        def delete_skill(row):
            skill_rows.remove(row)
            row.destroy()
            refresh_indices()
        
        def move_skill(row, positions):
            """Move a skill by N positions (positive = down, negative = up)"""
            idx = skill_rows.index(row)
            new_idx = max(0, min(len(skill_rows) - 1, idx + positions))
            if new_idx != idx:
                # Remove from current position and insert at new position
                skill_rows.remove(row)
                skill_rows.insert(new_idx, row)
                # Repack all rows
                for r in skill_rows:
                    r.pack_forget()
                for r in skill_rows:
                    r.pack(fill=tk.X, pady=2, padx=5)
                refresh_indices()
        
        def on_child_toggled(row, child_skill_name):
            """When child skill is toggled, remove variants of that skill from the list"""
            variants = get_skill_variants(child_skill_name)
            to_remove = [r for r in skill_rows if r.skill_name in variants and r != row]
            for r in to_remove:
                skill_rows.remove(r)
                r.destroy()
            refresh_indices()
        
        def add_skill(skill_name):
            if skill_name not in _skills_by_name:
                messagebox.showwarning("Unknown Skill", f"Skill '{skill_name}' not found in database.")
                return
            
            if any(r.skill_name == skill_name for r in skill_rows):
                messagebox.showinfo("Duplicate", f"'{skill_name}' is already in the list.")
                return
            
            row = SkillRowWidget(
                skills_scroll, skill_name, colors,
                on_delete=delete_skill,
                on_move=move_skill,
                on_toggle_child=on_child_toggled,
                index=len(skill_rows)
            )
            skill_rows.append(row)
            refresh_indices()
        
        # Add skill entry
        entry_frame = ctk.CTkFrame(window, fg_color=colors['bg_medium'], corner_radius=10)
        entry_frame.pack(fill=tk.X, padx=20, pady=10)
        
        autocomplete = SkillAutocompleteEntry(entry_frame, colors, on_select=add_skill)
        autocomplete.pack(pady=15, padx=15)
        
        # Scrollable skills area
        skills_scroll = ctk.CTkScrollableFrame(window, fg_color=colors['bg_medium'], corner_radius=10)
        skills_scroll.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        # Load existing skills
        for i, skill_name in enumerate(current_skills):
            if skill_name in _skills_by_name:
                child = gold_upgrades.get(skill_name, None)
                row = SkillRowWidget(
                    skills_scroll, skill_name, colors,
                    on_delete=delete_skill,
                    on_move=move_skill,
                    on_toggle_child=on_child_toggled,
                    index=i,
                    child_skill=child
                )
                skill_rows.append(row)
        
        # Bottom buttons
        btn_frame = ctk.CTkFrame(window, fg_color='transparent')
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        def save_skills():
            try:
                # Build skill_priority list
                skill_list = [row.skill_name for row in skill_rows]
                
                # Build gold_skill_upgrades dict (only for skills with child activated)
                gold_upgrades_out = {}
                for row in skill_rows:
                    if row.child_skill:
                        gold_upgrades_out[row.skill_name] = row.child_skill
                
                data = {
                    'skill_priority': skill_list,
                    'gold_skill_upgrades': gold_upgrades_out
                }
                
                with open(skill_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Saved", f"Saved {len(skill_list)} skills to {os.path.basename(skill_file)}")
                window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")
        
        ctk.CTkButton(btn_frame, text="Save", command=save_skills,
                     fg_color=colors['accent_green'], hover_color='#059669',
                     font=get_font('button'), width=100, height=35).pack(side=tk.RIGHT, padx=(5, 0))
        
        ctk.CTkButton(btn_frame, text="Cancel", command=window.destroy,
                     fg_color=colors['accent_red'], hover_color='#DC2626',
                     font=get_font('button'), width=100, height=35).pack(side=tk.RIGHT)
        
        ctk.CTkLabel(btn_frame, text=f"Editing: {os.path.basename(skill_file) if skill_file else 'Unknown'}",
                    text_color=colors['text_gray'],
                    font=get_font('body_small')).pack(side=tk.LEFT)
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open skill list window: {e}")
        import traceback
        traceback.print_exc()
