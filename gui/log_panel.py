import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, scrolledtext
from datetime import datetime

# Import centralized font management
try:
    from .font_manager import get_font_manager, get_font, get_font_tuple
except ImportError:
    from font_manager import get_font_manager, get_font, get_font_tuple

class LogPanel(ctk.CTkFrame):
    def __init__(self, parent, main_window, colors):
        super().__init__(parent, fg_color=colors['bg_medium'], corner_radius=15)
        self.main_window = main_window
        self.colors = colors

        # Title label
        title_label = ctk.CTkLabel(self, text="LOG", font=get_font('title_medium'), text_color=colors['text_light'])
        title_label.pack(pady=(15, 10))

        # Create log controls
        self.create_log_controls()

        # Create log display
        self.create_log_display()

        # Initialize auto-scroll
        self.auto_scroll_var = tk.BooleanVar(value=True)
    
    def create_log_controls(self):
        """Create the modern log control buttons above the log display"""
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        # START/STOP Button (modern rounded button)
        self.start_stop_btn = ctk.CTkButton(controls_frame, text="START", 
                                          command=self.toggle_bot, 
                                          fg_color=self.colors['accent_green'],
                                          hover_color="#2d5a27",
                                          corner_radius=8,
                                          width=80,
                                          height=32,
                                          font=get_font('button'))
        self.start_stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Auto-scroll Toggle (modern switch)
        auto_scroll_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        auto_scroll_frame.pack(side=tk.LEFT)
        
        ctk.CTkLabel(auto_scroll_frame, text="Auto-scroll:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.auto_scroll_btn = ctk.CTkButton(auto_scroll_frame, text="ON", 
                                           command=self.toggle_auto_scroll,
                                           fg_color=self.colors['accent_blue'],
                                           hover_color="#1f4a7a",
                                           corner_radius=8,
                                           width=50,
                                           height=32,
                                           font=get_font('button'))
        self.auto_scroll_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Log management buttons (modern rounded buttons)
        log_management_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        log_management_frame.pack(side=tk.RIGHT)
        
        ctk.CTkButton(log_management_frame, text="Clear Logs", 
                     command=self.clear_logs,
                     fg_color=self.colors['accent_yellow'],
                     hover_color="#6b5214",
                     corner_radius=8,
                     width=80,
                     height=32,
                     font=get_font('button')).pack(side=tk.LEFT, padx=(0, 5))
        ctk.CTkButton(log_management_frame, text="Save Logs", 
                     command=self.save_logs,
                     fg_color=self.colors['accent_blue'],
                     hover_color="#1f4a7a",
                     corner_radius=8,
                     width=80,
                     height=32,
                     font=get_font('button')).pack(side=tk.LEFT)
    
    def create_log_display(self):
        """Create the modern log text display area"""
        # Log display frame with rounded corners
        log_frame = ctk.CTkFrame(self, fg_color=self.colors['bg_light'], corner_radius=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Create scrolled text widget with modern dark theme and Unicode support
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=20,
            font=get_font_tuple('log_text'),  # Use defined log text font
            bg=self.colors['bg_light'],
            fg=self.colors['text_light'],
            insertbackground=self.colors['text_light'],
            selectbackground=self.colors['accent_blue'],
            selectforeground=self.colors['text_light'],
            relief=tk.FLAT,
            borderwidth=1,
            highlightthickness=0,
            wrap=tk.WORD,  # Enable word wrapping
            undo=False,    # Disable undo for better performance
            maxundo=0      # No undo history
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Configure tags for different log levels with modern colors
        self.log_text.tag_configure("info", foreground=self.colors['text_light'])
        self.log_text.tag_configure("warning", foreground="#ffab40")  # Modern orange
        self.log_text.tag_configure("error", foreground="#ff5252")    # Modern red
        self.log_text.tag_configure("success", foreground="#4caf50")  # Modern green
        self.log_text.tag_configure("debug", foreground=self.colors['text_gray'])
    
    def toggle_bot(self):
        """Toggle bot start/stop"""
        if self.main_window.bot_running:
            self.main_window.stop_bot()
        else:
            self.main_window.start_bot()
    
    def toggle_auto_scroll(self):
        """Toggle auto-scroll functionality"""
        self.auto_scroll_var.set(not self.auto_scroll_var.get())
        if self.auto_scroll_var.get():
            self.auto_scroll_btn.configure(text="ON", fg_color=self.colors['accent_blue'])
        else:
            self.auto_scroll_btn.configure(text="OFF", fg_color=self.colors['accent_red'])
    
    def update_start_stop_button(self, bot_running):
        """Update the START/STOP button appearance"""
        if bot_running:
            self.start_stop_btn.configure(text="STOP", fg_color=self.colors['accent_red'], hover_color="#651f2a")
        else:
            self.start_stop_btn.configure(text="START", fg_color=self.colors['accent_green'], hover_color="#2d5a27")
    
    def add_log_entry(self, log_entry, log_level="info"):
        """Add a log entry to the display with specified log level"""
        try:
            # Ensure the log entry is properly encoded as a string
            if not isinstance(log_entry, str):
                log_entry = str(log_entry)
            
            # Use provided log level or determine from content
            if log_level in ["info", "warning", "error", "success", "debug"]:
                tag = log_level
            else:
                # Fallback: determine log level from content
                tag = "info"
                if "ERROR" in log_entry.upper() or "FAILED" in log_entry.upper():
                    tag = "error"
                elif "WARNING" in log_entry.upper():
                    tag = "warning"
                elif "SUCCESS" in log_entry.upper() or "COMPLETED" in log_entry.upper():
                    tag = "success"
                elif "DEBUG" in log_entry.upper():
                    tag = "debug"
            
            # Add timestamp (GUI provides its own timestamp)
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_entry = f"[{timestamp}] {log_entry}"
            
            # Insert log entry with proper Unicode handling
            self.log_text.insert(tk.END, formatted_entry + "\n", tag)
            
            # Trim buffer if exceeds max lines to prevent memory issues
            max_lines = 1500
            line_count = int(self.log_text.index('end-1c').split('.')[0])
            if line_count > max_lines:
                # Delete oldest 500 lines to avoid frequent trimming
                self.log_text.delete('1.0', '501.0')
            
            # Auto-scroll if enabled
            if self.auto_scroll_var.get():
                self.log_text.see(tk.END)
                
        except Exception as e:
            # Fallback: try to insert without formatting if there's an error
            try:
                fallback_entry = f"[{datetime.now().strftime('%H:%M:%S')}] {str(log_entry)}"
                self.log_text.insert(tk.END, fallback_entry + "\n", "error")
                if self.auto_scroll_var.get():
                    self.log_text.see(tk.END)
            except:
                # Last resort: just print to console
                print(f"Failed to add log entry: {log_entry}")
                print(f"Error: {e}")
    
    def clear_logs(self):
        """Clear all logs from the display"""
        self.log_text.delete(1.0, tk.END)
        self.add_log_entry("[INFO] Logs cleared")
    
    def save_logs(self):
        """Save logs to a file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Logs As"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                self.add_log_entry(f"[INFO] Logs saved to {filename}")
            except Exception as e:
                self.add_log_entry(f"[ERROR] Failed to save logs: {e}")
    
    def get_log_content(self):
        """Get the current log content as string"""
        return self.log_text.get(1.0, tk.END)
    
    def set_log_content(self, content):
        """Set the log content from a string"""
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(1.0, content)
