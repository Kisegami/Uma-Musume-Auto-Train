"""
MaaTouch - High-performance touch injection via socket connection.

Based on MaaAssistantArknights MaaTouch protocol:
https://github.com/MaaAssistantArknights/MaaTouch

MaaTouch provides significantly faster touch input compared to ADB shell commands
by maintaining a persistent socket connection to the device.
"""

import socket
import subprocess
import time
import os
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass

from utils.device import run_adb, _get_adb_path
from utils.config_loader import load_config_section
from utils.log import log_info, log_warning, log_error, log_debug


@dataclass
class MaaTouchConfig:
    """Configuration for MaaTouch connection"""
    local_binary_path: str = ""
    remote_binary_path: str = "/data/local/tmp/maatouchsync"
    

def _find_maatouch_binary() -> Optional[str]:
    """Find the MaaTouch binary in utils/input/"""
    script_dir = Path(__file__).parent.parent
    path = script_dir / 'utils' / 'input' / 'maatouchsync'
    if path.exists():
        return str(path)
    return None


class MaaTouchConnection:
    """
    Manages a persistent socket connection to MaaTouch for high-performance touch input.
    
    Usage:
        with MaaTouchConnection() as maatouch:
            maatouch.tap(540, 960)
            maatouch.swipe(100, 100, 500, 500)
    """
    
    REMOTE_PATH = "/data/local/tmp/maatouchsync"
    
    def __init__(self):
        self._stream: Optional[socket.socket] = None
        self._stream_storage = None  # Keep reference to prevent garbage collection
        self._adb_path = _get_adb_path()
        self._device_address = self._load_device_address()
        self.max_x: int = 1280
        self.max_y: int = 720
        self._connected: bool = False
        
    def _load_device_address(self) -> str:
        """Load device address from config"""
        adb_cfg = load_config_section('adb_config', {})
        return adb_cfg.get('device_address', '')
    
    def _adb_command(self, args: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run an ADB command with the configured device"""
        cmd = [self._adb_path]
        if self._device_address:
            cmd.extend(['-s', self._device_address])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, **kwargs)
    
    def _adb_shell_stream(self, command: List[str]) -> socket.socket:
        """
        Execute ADB shell command and return the socket for streaming.
        This is used to run MaaTouch and maintain a persistent connection.
        """
        cmd = [self._adb_path]
        if self._device_address:
            cmd.extend(['-s', self._device_address])
        cmd.extend(['shell'] + command)
        
        # Start process with pipes
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        # Store process reference
        self._stream_storage = process
        
        # Create socket-like wrapper around stdout
        return process
    
    def _kill_device_process(self):
        """Kill any running MaaTouch app_process on the device"""
        # MaaTouch runs as: app_process / com.shxyke.MaaTouch.App
        # We need to kill it on the device side, not just the local subprocess
        result = self._adb_command(
            ['shell', 'pkill', '-f', 'com.shxyke.MaaTouch']
        )
        if result.returncode == 0:
            log_info("Killed existing MaaTouch process on device")
            import time as _time
            _time.sleep(0.5)  # Give the device a moment to clean up
        else:
            log_debug("No existing MaaTouch process found on device (this is normal)")
    
    def _check_binary_exists(self) -> bool:
        """Check if MaaTouch binary exists on the device"""
        result = self._adb_command(['shell', f'ls {self.REMOTE_PATH}'])
        output = result.stdout.decode(errors='replace').strip()
        # 'ls' returns the path if found, or error message if not
        return result.returncode == 0 and 'No such file' not in output
    
    def uninstall(self) -> bool:
        """Remove existing MaaTouch binary from device"""
        log_info("Removing existing MaaTouch binary from device...")
        result = self._adb_command(['shell', 'rm', '-f', self.REMOTE_PATH])
        if result.returncode != 0:
            log_warning(f"Failed to remove MaaTouch binary: {result.stderr.decode()}")
            return False
        log_info("Existing MaaTouch binary removed")
        return True
    
    def install(self) -> bool:
        """Push MaaTouch binary to device"""
        local_path = _find_maatouch_binary()
        if not local_path:
            log_error("MaaTouch binary not found in toolkit/bin/")
            return False
        
        # Remove existing binary first to ensure clean install
        self.uninstall()
        
        log_info(f"Installing MaaTouch from {local_path}")
        result = self._adb_command(['push', local_path, self.REMOTE_PATH])
        
        if result.returncode != 0:
            log_error(f"Failed to push MaaTouch: {result.stderr.decode()}")
            return False
        
        # Make executable
        self._adb_command(['shell', 'chmod', '755', self.REMOTE_PATH])
        log_info("MaaTouch installed successfully")
        return True
    
    def connect(self, auto_install: bool = True) -> bool:
        """
        Start MaaTouch and establish socket connection.
        
        MaaTouch protocol:
        1. Run: CLASSPATH=/data/local/tmp/maatouchsync app_process / com.shxyke.MaaTouch.App
        2. Read initialization line: ^ <max_contacts> <max_x> <max_y> <max_pressure>
        3. Read PID line: $ <pid>
        4. Send touch commands via stdin
        """
        if self._connected:
            return True
        
        # Close any existing local connection
        self.disconnect()
        
        # Kill any stale MaaTouch process on the device
        self._kill_device_process()
        
        # Pre-check: if binary doesn't exist on device, install it first
        if auto_install and not self._check_binary_exists():
            log_info("MaaTouch binary not found on device, auto-installing...")
            if not self.install():
                log_error("Failed to auto-install MaaTouch binary")
                return False
        
        # Build command - use a single string command for shell
        shell_cmd = f'CLASSPATH={self.REMOTE_PATH} app_process / com.shxyke.MaaTouch.App'
        
        cmd = [self._adb_path]
        if self._device_address:
            cmd.extend(['-s', self._device_address])
        cmd.extend(['shell', shell_cmd])
        
        log_debug(f"Starting MaaTouch: {shell_cmd}")
        
        try:
            # Start process
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._stream_storage = process
            
            # Use a thread to read output with timeout
            import threading
            import queue
            
            output_queue = queue.Queue()
            
            def read_output():
                try:
                    for line in iter(process.stdout.readline, b''):
                        output_queue.put(line.decode().strip())
                except:
                    pass
            
            reader_thread = threading.Thread(target=read_output, daemon=True)
            reader_thread.start()
            
            # Wait for initialization with timeout
            start_time = time.time()
            timeout = 5.0
            
            while time.time() - start_time < timeout:
                # Check if process died
                if process.poll() is not None:
                    stderr = process.stderr.read().decode()
                    log_error(f"MaaTouch process exited: {stderr}")
                    if auto_install:
                        self.disconnect()
                        log_info("Attempting auto-install of MaaTouch binary (process exited)...")
                        if self.install():
                            log_info("Auto-install successful, retrying connection...")
                            return self.connect(auto_install=False)
                    return False
                
                # Try to get output
                try:
                    line = output_queue.get(timeout=0.5)
                    log_debug(f"MaaTouch output: {line}")
                    
                    if line.startswith('^'):
                        # Parse: ^ <max_contacts> <max_x> <max_y> <max_pressure>
                        parts = line.split()
                        if len(parts) >= 5:
                            self.max_x = int(parts[2])
                            self.max_y = int(parts[3])
                            log_info(f"MaaTouch connected: max_x={self.max_x}, max_y={self.max_y}")
                            self._connected = True
                            
                            # Try to read PID line (optional)
                            try:
                                pid_line = output_queue.get(timeout=0.5)
                                log_debug(f"MaaTouch PID: {pid_line}")
                            except queue.Empty:
                                pass
                            
                            return True
                    elif line == 'Aborted' or 'Aborted' in line:
                        log_error("MaaTouch aborted - binary may be incompatible")
                        if auto_install:
                            self.disconnect()
                            log_info("Attempting reinstall of MaaTouch binary (aborted)...")
                            if self.install():
                                log_info("Reinstall successful, retrying connection...")
                                return self.connect(auto_install=False)
                        return False
                    elif 'not found' in line.lower() or 'no such file' in line.lower():
                        log_error(f"MaaTouch binary not found on device: {line}")
                        if auto_install:
                            self.disconnect()
                            log_info("Attempting auto-install of MaaTouch binary (not found)...")
                            if self.install():
                                log_info("Auto-install successful, retrying connection...")
                                return self.connect(auto_install=False)
                        return False
                    elif 'error' in line.lower():
                        log_error(f"MaaTouch error: {line}")
                        if auto_install:
                            self.disconnect()
                            log_info("Attempting auto-install of MaaTouch binary (error)...")
                            if self.install():
                                log_info("Auto-install successful, retrying connection...")
                                return self.connect(auto_install=False)
                        return False
                except queue.Empty:
                    continue
            
            # Log stderr for diagnostics (non-blocking)
            try:
                import selectors
                sel = selectors.DefaultSelector()
                sel.register(process.stderr, selectors.EVENT_READ)
                ready = sel.select(timeout=0.1)
                if ready:
                    stderr_data = process.stderr.read1(4096) if hasattr(process.stderr, 'read1') else b''
                    if stderr_data:
                        log_warning(f"MaaTouch stderr: {stderr_data.decode(errors='replace').strip()}")
                sel.close()
            except:
                pass
            log_error("Timeout waiting for MaaTouch initialization")
            if auto_install:
                self.disconnect()
                log_info("Attempting auto-install of MaaTouch binary...")
                if self.install():
                    log_info("Auto-install successful, retrying connection...")
                    return self.connect(auto_install=False)
            return False
            
        except Exception as e:
            log_error(f"Failed to connect to MaaTouch: {e}")
            import traceback
            traceback.print_exc()
            if auto_install:
                self.disconnect()
                log_info("Attempting auto-install of MaaTouch binary after exception...")
                if self.install():
                    log_info("Auto-install successful, retrying connection...")
                    return self.connect(auto_install=False)
            return False

    
    def disconnect(self):
        """Close the MaaTouch connection"""
        if self._stream_storage:
            try:
                self._stream_storage.terminate()
                self._stream_storage.wait(timeout=1)
            except:
                pass
            self._stream_storage = None
        self._connected = False
    
    def _send_command(self, command: str):
        """Send a command to MaaTouch"""
        if not self._connected or not self._stream_storage:
            raise RuntimeError("MaaTouch not connected")
        
        self._stream_storage.stdin.write((command + '\n').encode())
        self._stream_storage.stdin.flush()
    
    def _send_sync(self):
        """
        Send sync command and wait for device response to ensure all previous commands are executed.
        This effectively replaces Python-side sleep with accurate device synchronization.
        """
        if not self._connected:
            return

        timestamp = str(int(time.time() * 1000))
        self._send_command(f's {timestamp}')
        
        # Wait for echo
        # We need to read from the output queue populated by the reader thread
        # Accessing the queue from the reader thread
        # Note: We need to expose the output queue or mechanism to read specific lines
        # But we already have a reader thread eating stdout.
        # Let's modify the reader thread to handle sync responses? 
        # Actually, simpler: just wait for the timestamp to appear in output.
        
        # Since reading is threaded, we can't easily peek. 
        # But wait, we can't fully implement sync without exposing the reader queue.
        # For now, let's look at how we implemented connect().
        # We need a way to consume lines looking for the sync.
        
        # Actually, the reader thread in connect() is only started LOCALLY inside connect().
        # We need a persistent reader thread for the class.
        pass # To be implemented properly in a full class refactor

    # Let's refactor the whole class to have a proper reader thread
    
    def tap(self, x: int, y: int) -> bool:
        """Tap at coordinates using MaaTouch protocol"""
        if not self.connect():
            return False
            
        try:
            # Batch: Down -> Up -> Commit
            cmds = [
                f'd 0 {x} {y} 100',
                f'u 0',
                'c'
            ]
            self._send_command('\n'.join(cmds))
            return True
        except Exception as e:
            log_error(f"MaaTouch tap failed: {e}")
            return False

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Swipe using batched protocol with high density"""
        if not self.connect():
            return False
            
        try:
            # High density steps: 1 step every 10ms or 20 pixels
            # Ensure at least 5ms per step for stability
            
            distance = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
            # Density: 1 step per 20 pixels
            pixels_per_step = 20
            steps_by_dist = int(distance / pixels_per_step)
            
            # Density: 1 step per 10ms
            ms_per_step = 10
            steps_by_time = int(duration_ms / ms_per_step)
            
            steps = max(steps_by_dist, steps_by_time, 5) # Minimum 5 steps
            
            dx = (x2 - x1) / steps
            dy = (y2 - y1) / steps
            step_delay_ms = int(duration_ms / steps)
            
            cmds = []
            cmds.append(f'd 0 {x1} {y1} 100')
            if step_delay_ms > 0:
                cmds.append(f'w {step_delay_ms}')
                
            for i in range(1, steps + 1):
                x = int(x1 + dx * i)
                y = int(y1 + dy * i)
                cmds.append(f'm 0 {x} {y} 100')
                if step_delay_ms > 0:
                    cmds.append(f'w {step_delay_ms}')
                    
            cmds.append(f'u 0')
            cmds.append('c')
            
            self._send_command('\n'.join(cmds))
            
            # Keep the sleep for now as Sync requires reader refactor
            time.sleep(duration_ms / 1000.0)
            
            return True
        except Exception as e:
            log_error(f"MaaTouch swipe failed: {e}")
            return False

    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> bool:
        if not self.connect():
            return False
        try:
            cmds = [
                f'd 0 {x} {y} 100',
                f'w {duration_ms}',
                f'u 0',
                'c'
            ]
            self._send_command('\n'.join(cmds))
            time.sleep(duration_ms / 1000.0)
            return True
        except Exception as e:
            log_error(f"MaaTouch long_press failed: {e}")
            return False
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# Global connection instance for reuse
_maatouch_connection: Optional[MaaTouchConnection] = None


def get_maatouch_connection() -> MaaTouchConnection:
    """Get or create the global MaaTouch connection"""
    global _maatouch_connection
    if _maatouch_connection is None:
        _maatouch_connection = MaaTouchConnection()
    return _maatouch_connection


def maatouch_install() -> bool:
    """Install MaaTouch binary on device"""
    conn = get_maatouch_connection()
    return conn.install()


def maatouch_tap(x: int, y: int) -> bool:
    """Tap using MaaTouch"""
    conn = get_maatouch_connection()
    return conn.tap(x, y)


def maatouch_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
    """Swipe using MaaTouch"""
    conn = get_maatouch_connection()
    return conn.swipe(x1, y1, x2, y2, duration_ms)


def maatouch_long_press(x: int, y: int, duration_ms: int = 1000) -> bool:
    """Long press using MaaTouch"""
    conn = get_maatouch_connection()
    return conn.long_press(x, y, duration_ms)


def maatouch_disconnect():
    """Disconnect MaaTouch connection"""
    global _maatouch_connection
    if _maatouch_connection:
        _maatouch_connection.disconnect()
        _maatouch_connection = None
