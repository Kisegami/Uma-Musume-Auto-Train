import threading
import time
import subprocess
import sys
import os
import json
import queue
import re
from datetime import datetime
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QMetaObject, Qt, Q_ARG, QObject, Signal, Slot
from utils.emulator_detect import resolve_emulator_connection, EmulatorManager, Emulator
from utils.device import _get_adb_path


class LogSignaler(QObject):
    """Qt signal emitter for thread-safe GUI updates"""
    log_signal = Signal(str, str)  # message, level
    status_signal = Signal(dict)  # status data

class BotController:
    def __init__(self, main_window):
        self.main_window = main_window
        self.bot_running = False
        self.bot_thread = None
        self.status_update_thread = None
        self.log_monitor_thread = None
        self.bot_process = None  # Store process reference for termination
        
        # Qt signal emitter for thread-safe GUI updates
        self.signaler = LogSignaler()
        self.signaler.log_signal.connect(self._on_log_signal)
        self.signaler.status_signal.connect(self._on_status_signal)
        
        # Queues for communication between threads
        self.status_queue = queue.Queue()
        self.log_queue = queue.Queue()
        
        # Bot status data
        self.current_status = {
            'year': 'Unknown Year',
            'energy': 0.0,
            'turn': 'Unknown',
            'mood': 'Unknown',
            'goal_met': False,
            'stats': {
                'spd': 0,
                'sta': 0,
                'pwr': 0,
                'guts': 0,
                'wit': 0
            }
        }
        
        # Status update interval
        self.status_update_interval = 0.1  # 100ms for responsive updates
        
        # Start status update thread
        self.start_status_updates()
    
    @Slot(str, str)
    def _on_log_signal(self, message, level):
        """Handle log signal on main thread"""
        if hasattr(self.main_window, 'log_panel'):
            self.main_window.log_panel.add_log_entry(message, level)
    
    @Slot(dict)
    def _on_status_signal(self, status):
        """Handle status signal on main thread"""
        if hasattr(self.main_window, 'status_panel'):
            self.main_window.status_panel.update_from_bot_data(status)
    
    def start_status_updates(self):
        """Start the status update thread"""
        self.status_update_thread = threading.Thread(target=self.status_update_loop, daemon=True)
        self.status_update_thread.start()

    def prepare_emulator_connection(self) -> bool:
        """
        Validate emulator selection, resolve auto device address,
        and auto-pick screenshot method based on emulator type.
        """
        cfg = self.main_window.get_config()
        emulator_type = cfg.get("emulator_type", "").strip()
        if not emulator_type:
            QMessageBox.critical(None, "Emulator required", "Please choose an emulator type before starting.")
            return False

        adb_cfg = cfg.get("adb_config", {})
        # Use the smart ADB path resolver that checks bundled ADB and falls back gracefully
        try:
            adb_path = _get_adb_path()
        except Exception:
            # Fallback to config value if resolver fails
            adb_path = adb_cfg.get("adb_path", "adb")
        device_address = adb_cfg.get("device_address", "")

        manager = EmulatorManager()
        chosen_instance = None
        chosen_serial = None

        self.main_window.add_log(
            f"[auto-detect] emulator_type={emulator_type}, device_address={device_address}, capture_method={cfg.get('capture_method')}",
            "info"
        )

        if device_address == "auto":
            # Show candidates
            try:
                insts = manager.instances_by_type(emulator_type)
                self.main_window.add_log(
                    f"[auto-detect] found instances: {[f'{i.type}:{i.name}:{i.serial}' for i in insts]}",
                    "info"
                )
            except Exception as e:
                self.main_window.add_log(f"[auto-detect] instance listing failed: {e}", "warning")

            try:
                inst, serial, running = resolve_emulator_connection(emulator_type, adb_path=adb_path)
            except FileNotFoundError as e:
                # ADB not found - show user-friendly error
                error_msg = str(e)
                self.main_window.add_log(f"[auto-detect] ADB error: {error_msg}", "error")
                QMessageBox.critical(
                    None,
                    "ADB Not Found",
                    f"ADB executable not found.\n\n{error_msg}\n\n"
                    "Please configure ADB before starting the bot."
                )
                return False
            except Exception as e:
                # Other errors during emulator detection
                self.main_window.add_log(f"[auto-detect] Error: {e}", "error")
                QMessageBox.critical(None, "Emulator Detection Error", f"Failed to detect emulator: {e}")
                return False
            
            self.main_window.add_log(
                f"[auto-detect] adb running serials for type={emulator_type}: {running}",
                "info"
            )
            if serial is None:
                if not running:
                    QMessageBox.critical(
                        None,
                        "No emulator running",
                        "No running emulator detected for the selected type. "
                        "Please start the emulator and try again."
                    )
                    return False
                else:
                    QMessageBox.critical(
                        None,
                        "Multiple emulators",
                        "Multiple running emulators detected. Close others or set the ADB address manually."
                    )
                    return False
            chosen_instance, chosen_serial = inst, serial
            cfg.setdefault("adb_config", {})["device_address"] = serial
            self.main_window.set_config(cfg)
            self.main_window.add_log(f"Auto-selected ADB device: {serial}", "info")
        else:
            # Keep manual address; try to locate matching instance for downstream settings
            instances = manager.instances_by_type(emulator_type)
            chosen_instance = instances[0] if instances else None
            chosen_serial = device_address

        # Auto pick screenshot method
        cap_method = cfg.get("capture_method", "auto")
        if cap_method == "auto":
            if emulator_type == Emulator.MuMuPlayer12 and chosen_instance:
                cfg["capture_method"] = "nemu_ipc"
                exe_dir = os.path.dirname(chosen_instance.path)
                parent_dir = os.path.dirname(exe_dir)
                cfg.setdefault("nemu_ipc_config", {})
                cfg["nemu_ipc_config"]["nemu_folder"] = parent_dir
                cfg["nemu_ipc_config"]["instance_id"] = chosen_instance.mumu12_id or 0
                cfg["nemu_ipc_config"]["display_id"] = cfg["nemu_ipc_config"].get("display_id", 0)
                cfg["nemu_ipc_config"]["timeout"] = cfg["nemu_ipc_config"].get("timeout", 1.0)
                self.main_window.add_log(
                    f"Auto-set screenshot method to nemu_ipc for MuMuPlayer12 "
                    f"(folder={parent_dir}, instance_id={cfg['nemu_ipc_config']['instance_id']})",
                    "info"
                )
            elif emulator_type == Emulator.LDPlayer9 and chosen_instance:
                cfg["capture_method"] = "ldopengl"
                exe_dir = os.path.dirname(chosen_instance.path)
                cfg.setdefault("ldopengl_config", {})
                cfg["ldopengl_config"]["ld_folder"] = exe_dir
                if chosen_instance.ldplayer_id is not None:
                    cfg["ldopengl_config"]["instance_id"] = chosen_instance.ldplayer_id
                cfg["ldopengl_config"]["orientation"] = cfg["ldopengl_config"].get("orientation", 0)
                self.main_window.add_log(
                    f"Auto-set screenshot method to ldopengl for LDPlayer9 "
                    f"(ld_folder={exe_dir}, instance_id={cfg['ldopengl_config'].get('instance_id')})",
                    "info"
                )
            else:
                cfg["capture_method"] = "adb"
                self.main_window.add_log("Auto-set screenshot method to adb", "info")
        else:
            # If user already chose nemu_ipc/ldopengl but folder/instance missing, try to fill from detected instance.
            if emulator_type == Emulator.MuMuPlayer12 and chosen_instance:
                exe_dir = os.path.dirname(chosen_instance.path)
                parent_dir = os.path.dirname(exe_dir)
                cfg.setdefault("nemu_ipc_config", {})
                if not cfg["nemu_ipc_config"].get("nemu_folder"):
                    cfg["nemu_ipc_config"]["nemu_folder"] = parent_dir
                    self.main_window.add_log(
                        f"[auto-detect] Filled MuMu nemu_folder={parent_dir} from instance path", "info"
                    )
                if not cfg["nemu_ipc_config"].get("instance_id"):
                    cfg["nemu_ipc_config"]["instance_id"] = chosen_instance.mumu12_id or 0
            if emulator_type == Emulator.LDPlayer9 and chosen_instance:
                exe_dir = os.path.dirname(chosen_instance.path)
                cfg.setdefault("ldopengl_config", {})
                if not cfg["ldopengl_config"].get("ld_folder"):
                    cfg["ldopengl_config"]["ld_folder"] = exe_dir
                    self.main_window.add_log(
                        f"[auto-detect] Filled LDPlayer ld_folder={exe_dir} from instance path", "info"
                    )
                if cfg["ldopengl_config"].get("instance_id") in [None, ""]:
                    if chosen_instance.ldplayer_id is not None:
                        cfg["ldopengl_config"]["instance_id"] = chosen_instance.ldplayer_id

        # Sync updated config into main window before saving
        self.main_window.set_config(cfg)

        # Persist immediately so main.py sees resolved values
        try:
            # Force-sync main_window.config before saving
            self.main_window.config = cfg
            # Write to disk immediately with resolved values
            import json
            with open(self.main_window.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.main_window.config, f, indent=2, ensure_ascii=False)
            self.main_window.add_log("[auto-detect] config saved after resolving emulator/device/capture", "info")
            # Refresh main tab fields to reflect resolved values on the UI thread
            if hasattr(self.main_window, "config_panel") and hasattr(self.main_window.config_panel, "update_main_tab_from_config"):
                try:
                    resolved_cfg = self.main_window.get_config()
                    self.main_window.root.after(
                        0,
                        lambda: self.main_window.config_panel.update_main_tab_from_config(resolved_cfg)
                    )
                except Exception:
                    # Fallback to direct call if scheduling fails
                    self.main_window.config_panel.update_main_tab_from_config(cfg)
        except Exception as e:
            self.main_window.add_log(f"[auto-detect] failed to save config: {e}", "warning")

        return True
    
    def start_bot(self):
        """Start the bot automation"""
        if self.bot_running:
            return

        if not self.prepare_emulator_connection():
            return

        self.bot_running = True
        self.main_window.add_log("Starting Uma Musume Auto-Train Bot...", "info")
        
        # Start bot in separate thread
        self.bot_thread = threading.Thread(target=self.run_bot, daemon=True)
        self.bot_thread.start()
        
        # Start log monitoring thread
        self.log_monitor_thread = threading.Thread(target=self.monitor_bot_logs, daemon=True)
        self.log_monitor_thread.start()
    
    def stop_bot(self):
        """Stop the bot automation"""
        if not self.bot_running:
            return
        
        self.bot_running = False
        self.main_window.add_log("Stopping bot...", "warning")
        
        # Terminate the bot process if it's running
        if self.bot_process and hasattr(self.bot_process, 'poll'):
            try:
                self.main_window.add_log("Terminating bot process...", "info")
                self.bot_process.terminate()
                
                # Wait for process to terminate gracefully
                try:
                    self.bot_process.wait(timeout=5)
                    self.main_window.add_log("Bot process terminated gracefully", "success")
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    self.main_window.add_log("Force killing bot process...", "warning")
                    self.bot_process.kill()
                    self.bot_process.wait()
                    self.main_window.add_log("Bot process force killed", "warning")
                    
            except Exception as e:
                self.main_window.add_log(f"Error terminating bot process: {e}", "error")
            finally:
                self.bot_process = None
        
        # Wait for bot thread to finish
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=2)
        
        if self.log_monitor_thread and self.log_monitor_thread.is_alive():
            self.log_monitor_thread.join(timeout=1)
            
        self.main_window.add_log("Bot stopped successfully", "success")
    
    def run_bot(self):
        """Run the bot automation"""
        try:
            self.main_window.add_log("Bot started successfully", "success")
            self.main_window.add_log("Checking ADB connection...", "info")
            
            # Check if main script exists
            # Get project root directory (where main.py should be)
            # bot_controller.py is in gui/ folder, so go up one level to get project root
            try:
                # Get the directory containing this file (gui/), then go up one level
                current_file = os.path.abspath(__file__)
                gui_dir = os.path.dirname(current_file)
                project_root = os.path.dirname(gui_dir)
            except:
                # Fallback to current working directory
                project_root = os.getcwd()
            main_script = os.path.join(project_root, 'main.py')
            
            if os.path.exists(main_script):
                self.main_window.add_log("Found main.py, starting automation...", "info")
                
                try:
                    # Run the main ADB bot in a subprocess with unbuffered output
                    # Set cwd to project root so Python can find utils/ and other modules
                    env = os.environ.copy()
                    pythonpath = project_root
                    if "PYTHONPATH" in env:
                        pythonpath = pythonpath + os.pathsep + env["PYTHONPATH"]
                    env["PYTHONPATH"] = pythonpath
                    
                    env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered output

                    self.bot_process = subprocess.Popen(
                        [sys.executable, '-u', 'main.py'],  # -u for unbuffered output
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=0,  # Unbuffered
                        universal_newlines=True,
                        encoding='utf-8',  # Explicitly set UTF-8 encoding
                        errors='replace',   # Replace problematic characters instead of failing
                        cwd=project_root,  # Set working directory to project root
                        env=env  # Set PYTHONPATH
                    )
                    
                    self.main_window.add_log("Bot process started successfully", "success")
                    self.main_window.add_log(f"Process PID: {self.bot_process.pid}", "info")
                    self.main_window.add_log(f"Process poll: {self.bot_process.poll()}", "info")
                    
                    # Monitor the process output
                    self.main_window.add_log("Starting output monitor loop...", "info")
                    while self.bot_running and self.bot_process and self.bot_process.poll() is None:
                        try:
                            output = self.bot_process.stdout.readline()
                            if output:
                                # Process the output for status updates and logging
                                stripped = output.strip()
                                # process_bot_output handles adding to log queue
                                self.process_bot_output(stripped)
                            else:
                                # No output, but process might still be running
                                time.sleep(0.05)
                        except UnicodeDecodeError as e:
                            # Handle Unicode decoding errors gracefully
                            print(f"Unicode decode error in bot output: {e}")
                            try:
                                # Try to decode with error handling
                                if hasattr(output, 'decode'):
                                    decoded_output = output.decode('utf-8', errors='replace')
                                    self.process_bot_output(decoded_output.strip())
                            except Exception as decode_error:
                                print(f"Failed to decode output: {decode_error}")
                        except Exception as e:
                            self.main_window.add_log(f"Error reading bot output: {e}", "error")
                            break
                    
                    # Check if process finished
                    if self.bot_process and self.bot_process.poll() is not None:
                        self.main_window.add_log(f"Bot process finished with code: {self.bot_process.returncode}", "info")
                    else:
                        self.main_window.add_log("Bot process terminated", "warning")
                        
                except Exception as e:
                    self.main_window.add_log(f"Error running bot: {e}", "error")
                    # Clean up the process if it was created
                    if self.bot_process:
                        try:
                            self.bot_process.terminate()
                            self.bot_process = None
                        except:
                            pass
            else:
                self.main_window.add_log("main.py not found", "error")
                
        except Exception as e:
            self.main_window.add_log(f"Critical error in bot controller: {e}", "error")
        finally:
            # Clean up the process if it still exists
            if self.bot_process:
                try:
                    self.bot_process.terminate()
                    self.bot_process = None
                except:
                    pass
            self.bot_running = False
            self.main_window.add_log("Bot stopped", "warning")
            # Ensure main window state and button reflect auto-stop
            try:
                self.main_window.bot_running = False
                if hasattr(self.main_window, 'log_panel') and hasattr(self.main_window, 'root'):
                    # Update button on the main UI thread
                    self.main_window.root.after(0, self.main_window.log_panel.update_start_stop_button, False)
            except Exception:
                pass
    
    def process_bot_output(self, output):
        """Process bot output to extract status updates and logs"""
        if not output or not output.strip():
            return
        
        try:
            # Ensure output is properly encoded as a string
            if not isinstance(output, str):
                output = str(output)
            
            # Filter out unwanted shell output - only show actual logging messages
            if self.should_display_output(output):
                # Add to log queue for display
                self.log_queue.put(output)
            
            # Try to extract status information from the output
            self.extract_status_from_output(output)
        except Exception as e:
            # Log error but continue processing
            print(f"Error processing bot output: {e}")
            # Try to add the raw output to logs anyway
            try:
                if self.should_display_output(str(output)):
                    self.log_queue.put(str(output))
            except:
                pass
    
    def should_display_output(self, output):
        """Determine if output should be displayed in GUI log"""
        if not output or not isinstance(output, str):
            return False
        
        output_lower = output.lower().strip()
        
        # Filter out unwanted shell messages (be specific about what to exclude)
        unwanted_patterns = [
            'nemu_connect instance_name:',
            'connect not same day',
        ]
        
        # Check if output contains any unwanted patterns
        for pattern in unwanted_patterns:
            if pattern in output_lower:
                return False
        
        # Show lines that contain standard logging level indicators
        if re.search(r'\b(INFO|WARNING|ERROR|DEBUG|SUCCESS)\b', output, re.IGNORECASE):
            return True
        
        # Show lines that start with timestamps (common logging format)
        if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', output):
            return True
        
        # Show lines with brackets indicating log levels
        if re.search(r'\[(INFO|WARNING|ERROR|DEBUG|SUCCESS)\]', output, re.IGNORECASE):
            return True
        
        # Show lines with common logging format patterns
        if re.search(r'- (INFO|WARNING|ERROR|DEBUG|SUCCESS) -', output, re.IGNORECASE):
            return True
        
        # If it doesn't match unwanted patterns and has some content, show it
        # This is more permissive approach - exclude specific bad patterns rather than only include specific good ones
        if len(output.strip()) > 0:
            return True
        
        return False
    
    def extract_status_from_output(self, output):
        """Extract status information from bot output"""
        try:
            # Ensure output is a string and handle any encoding issues
            if not isinstance(output, str):
                output = str(output)
            
            # Extract year information
            year_match = re.search(r'Year:\s*(.+)', output)
            if year_match:
                year = year_match.group(1).strip()
                self.update_status('year', year)
            
            # Extract energy information
            energy_match = re.search(r'Energy:\s*([\d.]+)%', output)
            if energy_match:
                energy = float(energy_match.group(1))
                self.update_status('energy', energy)
            
            # Extract turn information
            turn_match = re.search(r'Turn:\s*(.+)', output)
            if turn_match:
                turn = turn_match.group(1).strip()
                self.update_status('turn', turn)
            
            # Extract mood information
            mood_match = re.search(r'Mood:\s*(.+)', output)
            if mood_match:
                mood = mood_match.group(1).strip()
                self.update_status('mood', mood)
            
            # Extract goal status
            goal_match = re.search(r'Status:\s*(.+)', output)
            if goal_match:
                goal_text = goal_match.group(1).strip()
                # Check if goal is met (criteria met)
                goal_met = "criteria met" in goal_text.lower() or "goal achieved" in goal_text.lower()
                self.update_status('goal_met', goal_met)
            
            # Extract stats
            stats_match = re.search(r'Current stats:\s*(.+)', output)
            if stats_match:
                stats_text = stats_match.group(1)
                stats = self.parse_stats_from_text(stats_text)
                if stats:
                    self.update_status('stats', stats, partial=True)
            
                    
        except Exception as e:
            # Don't log parsing errors to avoid spam, but print to console for debugging
            print(f"Error extracting status from output: {e}")
            pass
    
    def parse_stats_from_text(self, stats_text):
        """Parse stats from text like 'SPD: 244, STA: 176, PWR: 166, GUTS: 99, WIT: 126'"""
        try:
            if not stats_text or not isinstance(stats_text, str):
                return {}
            
            # Ensure the text is properly encoded
            stats_text = str(stats_text)
                
            stats = {}
            # Look for patterns like "spd: 123", "sta: 456", etc.
            for stat in ['spd', 'sta', 'pwr', 'guts', 'wit']:
                match = re.search(f'{stat}:\\s*(\\d+)', stats_text, re.IGNORECASE)
                if match:
                    stats[stat] = int(match.group(1))
            return stats
        except Exception as e:
            print(f"Error parsing stats from text: {e}")
            return {}
    
    def update_status(self, field, value, partial=False):
        """Update status field and queue for GUI update"""
        if field == 'stats':
            if partial:
                # Partial update - only update specific stats
                self.current_status['stats'].update(value)
            else:
                # Full update - replace all stats
                self.current_status['stats'] = value
        else:
            self.current_status[field] = value
        
        # Queue status update for GUI
        self.status_queue.put(self.current_status.copy())
    
    def status_update_loop(self):
        """Main status update loop that runs continuously"""
        while True:
            try:
                # Check for status updates
                try:
                    while not self.status_queue.empty():
                        status = self.status_queue.get_nowait()
                        # Emit signal (thread-safe Qt way)
                        self.signaler.status_signal.emit(status)
                except queue.Empty:
                    pass
                
                # Check for log updates
                try:
                    while not self.log_queue.empty():
                        log_entry = self.log_queue.get_nowait()
                        # Emit signal (thread-safe Qt way)
                        level = self.determine_log_level(log_entry)
                        self.signaler.log_signal.emit(log_entry, level)
                except queue.Empty:
                    pass
                
                time.sleep(self.status_update_interval)
                
            except Exception as e:
                # Log error but continue running
                print(f"Error in status update loop: {e}")
                time.sleep(1)
    
    def update_gui_status(self, status):
        """Update GUI status panel (called from main thread)"""
        try:
            if hasattr(self.main_window, 'status_panel'):
                self.main_window.status_panel.update_from_bot_data(status)
        except Exception as e:
            print(f"Error updating GUI status: {e}")
    
    def add_log_to_gui(self, log_entry):
        """Add log entry to GUI (called from main thread)"""
        try:
            if hasattr(self.main_window, 'log_panel'):
                # Determine log level based on content
                log_level = self.determine_log_level(log_entry)
                self.main_window.log_panel.add_log_entry(log_entry, log_level)
        except Exception as e:
            print(f"Error adding log to GUI: {e}")
    
    def determine_log_level(self, log_entry):
        """Determine log level based on log entry content"""
        try:
            if not log_entry or not isinstance(log_entry, str):
                return 'info'
                
            log_lower = log_entry.lower()
            
            if any(word in log_lower for word in ['error', 'failed', 'exception']):
                return 'error'
            elif any(word in log_lower for word in ['warning', 'warn']):
                return 'warning'
            elif any(word in log_lower for word in ['success', 'completed', 'found']):
                return 'success'
            elif any(word in log_lower for word in ['debug']):
                return 'debug'
            else:
                return 'info'
        except Exception:
            return 'info'
    
    def monitor_bot_logs(self):
        """Monitor bot logs for real-time updates"""
        while self.bot_running:
            try:
                # This thread is now handled by the main status update loop
                time.sleep(0.1)
            except Exception as e:
                print(f"Error in log monitor: {e}")
                break
    
    def get_current_status(self):
        """Get current bot status"""
        try:
            return self.current_status.copy()
        except Exception:
            return {}
    
    def is_bot_running(self):
        """Check if bot is currently running"""
        return self.bot_running
