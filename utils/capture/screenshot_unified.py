import os
import json
import ctypes
import time
import statistics
import subprocess
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from typing import Optional, Union
from PIL import Image, ImageEnhance
import numpy as np
import cv2
from utils.platform.device import run_adb
from utils.core.log import log_debug, log_info, log_warning, log_error
from utils.core.config_loader import load_main_config


class NemuIpcIncompatible(Exception):
    """Raised when Nemu IPC is not available or compatible"""
    pass


class NemuIpcError(Exception):
    """Raised when Nemu IPC operations fail"""
    pass


class LDOpenGLIncompatible(Exception):
    """Raised when LDOpenGL is not available or compatible"""
    pass


class LDOpenGLError(Exception):
    """Raised when LDOpenGL operations fail"""
    pass


class NemuIpcCapture:
    """Nemu IPC capture implementation for faster screenshots"""

    def __init__(self, nemu_folder: str, instance_id: int, display_id: int = 0, timeout: float = 1.0, verbose: bool = False):
        self.nemu_folder = nemu_folder
        self.instance_id = instance_id
        self.display_id = display_id
        self.timeout = timeout
        self.verbose = verbose
        self.connect_id = 0
        self.width = 0
        self.height = 0

        # Try to load DLL from possible locations
        candidates = [
            os.path.abspath(os.path.join(nemu_folder, './shell/sdk/external_renderer_ipc.dll')),
            os.path.abspath(os.path.join(nemu_folder, './nx_device/12.0/shell/sdk/external_renderer_ipc.dll')),
        ]
        self.lib = None
        last_err = None
        for dll in candidates:
            if not os.path.exists(dll):
                continue
            try:
                self.lib = ctypes.CDLL(dll)
                break
            except OSError as e:
                last_err = e
                continue
        if self.lib is None:
            raise NemuIpcIncompatible(
                f'Cannot load external_renderer_ipc.dll. Tried: {candidates}. Last error: {last_err}'
            )

        # Function prototypes
        try:
            self.lib.nemu_connect.restype = ctypes.c_int
        except Exception:
            pass
        try:
            self.lib.nemu_disconnect.argtypes = [ctypes.c_int]
            self.lib.nemu_disconnect.restype = ctypes.c_int
        except Exception:
            pass

        self.lib.nemu_capture_display.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int), ctypes.c_void_p
        ]
        self.lib.nemu_capture_display.restype = ctypes.c_int

        self._executor = ThreadPoolExecutor(max_workers=1)

    @staticmethod
    def serial_to_id(serial: str) -> Optional[int]:
        """Convert ADB serial to Nemu instance ID"""
        try:
            port = int(serial.split(':')[1])
        except (IndexError, ValueError):
            return None
        index, offset = divmod(port - 16384 + 16, 32)
        offset -= 16
        if 0 <= index < 32 and offset in [-2, -1, 0, 1, 2]:
            return index
        return None

    def _run_with_timeout(self, func, *args, timeout: Optional[float] = None):
        if timeout is None:
            return func(*args)
        fut = self._executor.submit(func, *args)
        try:
            return fut.result(timeout=timeout)
        except TimeoutError:
            fut.cancel()
            raise NemuIpcError('IPC call timeout')

    def connect(self, timeout: Optional[float] = None):
        """Connect to Nemu emulator"""
        if self.connect_id:
            return
        
        # Simple connection - DLL messages will go to console but won't affect GUI
        cid = self.lib.nemu_connect(self.nemu_folder, int(self.instance_id))
        if cid == 0 and timeout is not None:
            folder_bytes = os.fsencode(self.nemu_folder)
            cid = self._run_with_timeout(self.lib.nemu_connect, folder_bytes, int(self.instance_id), timeout=timeout)
        if cid == 0:
            raise NemuIpcError('nemu_connect failed. Check folder path and that emulator is running')
        self.connect_id = int(cid)

    def disconnect(self):
        """Disconnect from Nemu emulator"""
        if not self.connect_id:
            return
        try:
            self.lib.nemu_disconnect(int(self.connect_id))
        finally:
            self.connect_id = 0

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def get_resolution(self, timeout: Optional[float] = None):
        """Get screen resolution"""
        if not self.connect_id:
            self.connect(timeout=timeout)
        w_ptr = ctypes.pointer(ctypes.c_int(0))
        h_ptr = ctypes.pointer(ctypes.c_int(0))
        null = ctypes.c_void_p()
        ret = self._run_with_timeout(
            self.lib.nemu_capture_display,
            int(self.connect_id), int(self.display_id), 0, w_ptr, h_ptr, null,
            timeout=timeout,
        )
        if int(ret) > 0:
            raise NemuIpcError('nemu_capture_display failed in get_resolution')
        self.width = w_ptr.contents.value
        self.height = h_ptr.contents.value

    def screenshot(self, timeout: Optional[float] = None) -> np.ndarray:
        """Take screenshot using Nemu IPC"""
        if not self.connect_id:
            self.connect(timeout=timeout)
        if self.width == 0 or self.height == 0:
            self.get_resolution(timeout=timeout)
        w_ptr = ctypes.pointer(ctypes.c_int(int(self.width)))
        h_ptr = ctypes.pointer(ctypes.c_int(int(self.height)))
        length = int(self.width * self.height * 4)
        pixels = (ctypes.c_ubyte * length)()
        ret = self._run_with_timeout(
            self.lib.nemu_capture_display,
            int(self.connect_id), int(self.display_id), length, w_ptr, h_ptr, ctypes.byref(pixels),
            timeout=timeout,
        )
        if int(ret) > 0:
            raise NemuIpcError('nemu_capture_display failed in screenshot')
        # Build numpy array from ctypes buffer
        arr = np.frombuffer(pixels, dtype=np.uint8)
        arr = arr.reshape((int(self.height), int(self.width), 4))
        return arr


def bytes_to_str(b: bytes) -> str:
    """Convert bytes to string, trying multiple encodings."""
    for encoding in ['utf-8', 'gbk']:
        try:
            return b.decode(encoding)
        except UnicodeDecodeError:
            pass
    return str(b)


@dataclass
class DataLDPlayerInfo:
    """LDPlayer instance information."""
    index: int
    name: str
    topWnd: int
    bndWnd: int
    sysboot: int
    playerpid: int
    vboxpid: int
    width: int
    height: int
    dpi: int

    def __post_init__(self):
        self.index = int(self.index)
        self.name = bytes_to_str(self.name)
        self.topWnd = int(self.topWnd)
        self.bndWnd = int(self.bndWnd)
        self.sysboot = int(self.sysboot)
        self.playerpid = int(self.playerpid)
        self.vboxpid = int(self.vboxpid)
        self.width = int(self.width)
        self.height = int(self.height)
        self.dpi = int(self.dpi)


class LDConsole:
    """Wrapper for ldconsole.exe commands."""
    
    def __init__(self, ld_folder: str):
        self.ld_console = os.path.abspath(os.path.join(ld_folder, './ldconsole.exe'))
        if not os.path.exists(self.ld_console):
            raise LDOpenGLIncompatible(f'ldconsole.exe not found: {self.ld_console}')

    def subprocess_run(self, cmd, timeout=10):
        cmd = [self.ld_console] + cmd
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
            stdout, _ = process.communicate(timeout=timeout)
            return stdout
        except FileNotFoundError as e:
            raise LDOpenGLIncompatible(f'Cannot execute {cmd}: {e}')
        except subprocess.TimeoutExpired:
            process.kill()
            return b''

    def list2(self):
        """List all LDPlayer instances."""
        out = []
        data = self.subprocess_run(['list2'])
        for row in data.strip().split(b'\n'):
            row = row.strip()
            if not row:
                continue
            parts = row.split(b',')
            if len(parts) == 10:
                try:
                    out.append(DataLDPlayerInfo(*parts))
                except Exception:
                    pass
        return out


class IScreenShotClass:
    """Wrapper for IScreenShotClass from ldopengl64.dll."""
    
    def __init__(self, ptr):
        self.ptr = ptr
        cap_type = ctypes.WINFUNCTYPE(ctypes.c_void_p)
        release_type = ctypes.WINFUNCTYPE(None)
        self.class_cap = cap_type(1, "IScreenShotClass_Cap")
        self.class_release = release_type(2, "IScreenShotClass_Release")

    def cap(self):
        return self.class_cap(self.ptr)

    def __del__(self):
        if hasattr(self, 'class_release'):
            self.class_release(self.ptr)


class LDOpenGLCapture:
    """LDOpenGL capture implementation for faster screenshots on LDPlayer."""
    
    def __init__(self, ld_folder: str, instance_id: int, orientation: int = 0):
        """
        Args:
            ld_folder: Installation path of LDPlayer
            instance_id: Emulator instance ID, starting from 0
            orientation: Device orientation (0=normal, 2=upside down)
        """
        self.ld_folder = ld_folder
        self.instance_id = instance_id
        self.orientation = orientation
        self.width = 0
        self.height = 0
        
        ldopengl_dll = os.path.abspath(os.path.join(ld_folder, './ldopengl64.dll'))
        
        try:
            self.lib = ctypes.WinDLL(ldopengl_dll)
        except OSError as e:
            if not os.path.exists(ldopengl_dll):
                raise LDOpenGLIncompatible(
                    f'ldopengl64.dll not found. Requires LDPlayer >= 9.0.78'
                )
            raise LDOpenGLIncompatible(f'Cannot load DLL: {e}')
        
        self.console = LDConsole(ld_folder)
        self.info = self.get_player_info_by_index(instance_id)
        self.width = self.info.width
        self.height = self.info.height
        
        self.lib.CreateScreenShotInstance.restype = ctypes.c_void_p
        instance_ptr = ctypes.c_void_p(
            self.lib.CreateScreenShotInstance(instance_id, self.info.playerpid)
        )
        self.screenshot_instance = IScreenShotClass(instance_ptr)

    def get_player_info_by_index(self, instance_id: int):
        """Get LDPlayer instance info by index."""
        for info in self.console.list2():
            if info.index == instance_id:
                if not info.sysboot:
                    raise LDOpenGLError(f'Instance {instance_id} is not running')
                return info
        raise LDOpenGLError(f'No instance with index {instance_id}')

    @staticmethod
    def serial_to_id(serial: str) -> Optional[int]:
        """Predict instance ID from ADB serial."""
        try:
            if ':' in serial:
                port = int(serial.split(':')[1])
                if 5555 <= port <= 5555 + 32:
                    return (port - 5555) // 2
            elif serial.startswith('emulator-'):
                port = int(serial.replace('emulator-', ''))
                if 5554 <= port <= 5554 + 32:
                    return (port - 5554) // 2
        except (ValueError, IndexError):
            pass
        return None

    def screenshot(self) -> Image.Image:
        """Take screenshot using LDOpenGL."""
        img_ptr = self.screenshot_instance.cap()
        if img_ptr is None:
            raise LDOpenGLError('Empty image pointer')
        
        width, height = self.info.width, self.info.height
        img = ctypes.cast(
            img_ptr, 
            ctypes.POINTER(ctypes.c_ubyte * (height * width * 3))
        ).contents
        image = np.ctypeslib.as_array(img).reshape((height, width, 3))
        
        # Process: flip and convert BGR to RGB
        if self.orientation == 2:
            image = cv2.flip(image, 1)  # Horizontal flip
        else:
            image = cv2.flip(image, 0)  # Vertical flip (raw data is upside down)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to RGBA for PIL
        rgba = np.zeros((height, width, 4), dtype=np.uint8)
        rgba[:, :, :3] = image
        rgba[:, :, 3] = 255  # Alpha channel
        
        return Image.fromarray(rgba, 'RGBA')

    def get_resolution(self):
        """Get screen resolution."""
        return self.width, self.height


class AdbCapture:
    """ADB capture implementation (existing functionality)"""

    def __init__(self, config: dict):
        self.config = config

    def screenshot(self) -> Image.Image:
        """Take screenshot using ADB"""
        try:
            result = run_adb(['shell', 'screencap'], binary=True, add_input_delay=False)
            if result is None:
                raise Exception("Failed to take screenshot")

            cleaned_result = result.replace(b'\r\n', b'\n')  # Remove carriage returns

            # Parse the header: width (4 bytes), height (4 bytes), format (4 bytes), unknown (4 bytes)
            width = int.from_bytes(cleaned_result[0:4], byteorder='little')
            height = int.from_bytes(cleaned_result[4:8], byteorder='little')

            pixel_data = cleaned_result[16:]  # Skip the header (16 bytes)

            img = Image.frombytes('RGBA', (width, height), pixel_data)
            return img
        except Exception as e:
            log_error(f"Error taking ADB screenshot: {e}")
            raise


class UnifiedScreenshot:
    """Unified screenshot system that can use ADB, Nemu IPC, or LDOpenGL"""

    def __init__(self):
        self.config = self._load_config()
        self.capture_method = self.config.get('capture_method', 'adb')
        self.nemu_capture = None
        self.ldopengl_capture = None
        self.adb_capture = None

        # Initialize capture method
        if self.capture_method == 'nemu_ipc':
            try:
                nemu_config = self.config.get('nemu_ipc_config', {})
                self.nemu_capture = NemuIpcCapture(
                    nemu_folder=nemu_config.get('nemu_folder', 'J:\\MuMuPlayerGlobal'),
                    instance_id=nemu_config.get('instance_id', 2),
                    display_id=nemu_config.get('display_id', 0),
                    timeout=nemu_config.get('timeout', 1.0),
                    verbose=False
                )
                if not hasattr(self, '_nemu_initialized'):
                    log_info(f"Initialized Nemu IPC capture with method: {self.capture_method}")
                    log_info("Note: DLL connection messages may appear in console (won't affect GUI)")
                    self._nemu_initialized = True
            except Exception as e:
                log_error(f"Failed to initialize Nemu IPC capture: {e}")
                log_info("Falling back to ADB capture")
                self.capture_method = 'adb'

        elif self.capture_method == 'ldopengl':
            if os.name != 'nt':
                log_warning("LDOpenGL only works on Windows, falling back to ADB")
                self.capture_method = 'adb'
            else:
                try:
                    ldopengl_config = self.config.get('ldopengl_config', {})
                    ld_folder = ldopengl_config.get('ld_folder', '')
                    instance_id = ldopengl_config.get('instance_id', 0)
                    orientation = ldopengl_config.get('orientation', 0)
                    
                    # Use device_address from adb_config for auto-detection
                    adb_config = self.config.get('adb_config', {})
                    device_address = adb_config.get('device_address', '')
                    
                    # Try to auto-detect instance_id from device_address if not provided
                    if instance_id == 0 and device_address:
                        auto_id = LDOpenGLCapture.serial_to_id(device_address)
                        if auto_id is not None:
                            instance_id = auto_id
                            log_info(f"Auto-detected LDPlayer instance ID {instance_id} from device_address")
                    
                    if not ld_folder:
                        raise LDOpenGLIncompatible("ld_folder not configured in ldopengl_config")
                    
                    self.ldopengl_capture = LDOpenGLCapture(
                        ld_folder=ld_folder,
                        instance_id=instance_id,
                        orientation=orientation
                    )
                    if not hasattr(self, '_ldopengl_initialized'):
                        log_info(f"Initialized LDOpenGL capture: {self.ldopengl_capture.info.name} "
                                f"({self.ldopengl_capture.width}x{self.ldopengl_capture.height})")
                        self._ldopengl_initialized = True
                except (LDOpenGLIncompatible, LDOpenGLError) as e:
                    log_error(f"Failed to initialize LDOpenGL capture: {e}")
                    log_info("Falling back to ADB capture")
                    self.capture_method = 'adb'
                except Exception as e:
                    log_error(f"Unexpected error initializing LDOpenGL: {e}")
                    log_info("Falling back to ADB capture")
                    self.capture_method = 'adb'

        if self.capture_method == 'adb':
            self.adb_capture = AdbCapture(self.config.get('adb_config', {}))
            if not hasattr(self, '_adb_initialized'):
                log_info(f"Using ADB capture method: {self.capture_method}")
                self._adb_initialized = True

    def _load_config(self) -> dict:
        """Load configuration from config.json"""
        try:
            return load_main_config()
        except Exception as e:
            log_error(f"Error loading config: {e}")
            return {}

    def take_screenshot(self) -> Image.Image:
        """Take screenshot using the configured capture method"""
        if self.capture_method == 'nemu_ipc' and self.nemu_capture:
            try:
                with self.nemu_capture:
                    rgba_array = self.nemu_capture.screenshot()
                    flipped_array = np.flip(rgba_array, axis=0)
                    return Image.fromarray(flipped_array, 'RGBA')
            except Exception as e:
                log_error(f"Nemu IPC capture failed: {e}")
                log_info("Falling back to ADB capture")
                self.capture_method = 'adb'

        elif self.capture_method == 'ldopengl' and self.ldopengl_capture:
            try:
                return self.ldopengl_capture.screenshot()
            except (LDOpenGLError, LDOpenGLIncompatible) as e:
                log_error(f"LDOpenGL capture failed: {e}")
                log_info("Falling back to ADB capture")
                self.capture_method = 'adb'
            except Exception as e:
                log_error(f"Unexpected LDOpenGL error: {e}")
                log_info("Falling back to ADB capture")
                self.capture_method = 'adb'

        # Fallback to ADB capture
        if self.adb_capture:
            return self.adb_capture.screenshot()
        else:
            self.adb_capture = AdbCapture(self.config.get('adb_config', {}))
            return self.adb_capture.screenshot()

    def get_screen_size(self) -> tuple:
        """Get screen size"""
        try:
            if self.capture_method == 'nemu_ipc' and self.nemu_capture:
                with self.nemu_capture:
                    self.nemu_capture.get_resolution()
                    return self.nemu_capture.width, self.nemu_capture.height
            elif self.capture_method == 'ldopengl' and self.ldopengl_capture:
                return self.ldopengl_capture.get_resolution()
            else:
                # Fallback to ADB method
                result = run_adb(['shell', 'wm', 'size'])
                if result:
                    if 'Physical size:' in result:
                        size_part = result.split('Physical size:')[1].strip()
                        width, height = map(int, size_part.split('x'))
                        return width, height
                    else:
                        width, height = map(int, result.split('x'))
                        return width, height
                else:
                    # Fallback: take a screenshot and get its size
                    screenshot = self.take_screenshot()
                    return screenshot.size
        except Exception as e:
            log_error(f"Error getting screen size: {e}")
            return 1080, 1920

    def enhanced_screenshot(self, region, screenshot=None):
        """Take a screenshot of a specific region with enhancement"""
        try:
            if screenshot is None:
                screenshot = self.take_screenshot()
            cropped = screenshot.crop(region)

            # Resize for better OCR (same as PC version)
            cropped = cropped.resize((cropped.width * 2, cropped.height * 2), Image.BICUBIC)

            # Convert to grayscale (same as PC version)
            cropped = cropped.convert("L")

            # Enhance contrast (same as PC version)
            enhancer = ImageEnhance.Contrast(cropped)
            enhanced = enhancer.enhance(1.5)

            return enhanced
        except Exception as e:
            log_error(f"Error taking enhanced screenshot: {e}")
            raise

    def enhanced_screenshot_for_failure(self, region, screenshot=None):
        """Enhanced screenshot specifically optimized for white and yellow text on orange background"""
        try:
            if screenshot is None:
                screenshot = self.take_screenshot()
            cropped = screenshot.crop(region)

            # Resize for better OCR
            cropped = cropped.resize((cropped.width * 2, cropped.height * 2), Image.BICUBIC)

            # Convert to RGB to work with color channels
            cropped = cropped.convert("RGB")

            # Convert to numpy for color processing
            img_np = np.array(cropped)

            # Define orange color range (RGB) - for background
            orange_mask = (
                (img_np[:, :, 0] > 150) &  # High red
                (img_np[:, :, 1] > 80) &   # Medium green
                (img_np[:, :, 2] < 100)    # Low blue
            )

            # Define white text range (RGB) - for "Failure" text
            white_mask = (
                (img_np[:, :, 0] > 200) &  # High red
                (img_np[:, :, 1] > 200) &  # High green
                (img_np[:, :, 2] > 200)    # High blue
            )

            # Define yellow text range (RGB) - for failure rate percentages
            yellow_mask = (
                (img_np[:, :, 0] > 190) &  # High red
                (img_np[:, :, 1] > 140) &  # High green
                (img_np[:, :, 2] < 90)     # Low blue
            )

            # Create a new image: black background, white and yellow text
            result = np.zeros_like(img_np)

            # Set white text (for "Failure")
            result[white_mask] = [255, 255, 255]

            # Set yellow text (for percentages) - convert to white for OCR
            result[yellow_mask] = [255, 255, 255]

            # Set orange background to black
            result[orange_mask] = [0, 0, 0]

            # Convert back to PIL
            pil_img = Image.fromarray(result)

            # Convert to grayscale for OCR
            pil_img = pil_img.convert("L")

            # Enhance contrast for better OCR
            pil_img = ImageEnhance.Contrast(pil_img).enhance(1.5)

            return pil_img
        except Exception as e:
            log_error(f"Error taking failure screenshot: {e}")
            raise

    def enhanced_screenshot_for_year(self, region, screenshot=None):
        """Take a screenshot optimized for year detection"""
        try:
            if screenshot is None:
                screenshot = self.take_screenshot()
            cropped = screenshot.crop(region)

            # Enhance for year text detection
            enhancer = ImageEnhance.Contrast(cropped)
            enhanced = enhancer.enhance(2.5)

            enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = enhancer.enhance(2.0)

            return enhanced
        except Exception as e:
            log_error(f"Error taking year screenshot: {e}")
            raise

    def capture_region(self, region):
        """Capture a specific region of the screen"""
        try:
            screenshot = self.take_screenshot()
            return screenshot.crop(region)
        except Exception as e:
            log_error(f"Error capturing region: {e}")
            raise


# Global instance for backward compatibility
_unified_screenshot = None


def get_unified_screenshot() -> UnifiedScreenshot:
    """Get or create the global unified screenshot instance"""
    global _unified_screenshot
    if _unified_screenshot is None:
        _unified_screenshot = UnifiedScreenshot()
    return _unified_screenshot


def take_screenshot() -> Image.Image:
    """Take screenshot using the configured capture method (backward compatibility)"""
    return get_unified_screenshot().take_screenshot()


def get_screen_size() -> tuple:
    """Get screen size using the configured capture method (backward compatibility)"""
    return get_unified_screenshot().get_screen_size()


def enhanced_screenshot(region, screenshot=None):
    """Take a screenshot of a specific region with enhancement (backward compatibility)"""
    try:
        if screenshot is None:
            screenshot = take_screenshot()
        cropped = screenshot.crop(region)

        # Resize for better OCR (same as PC version)
        cropped = cropped.resize((cropped.width * 2, cropped.height * 2), Image.BICUBIC)

        # Convert to grayscale (same as PC version)
        cropped = cropped.convert("L")

        # Enhance contrast (same as PC version)
        enhancer = ImageEnhance.Contrast(cropped)
        enhanced = enhancer.enhance(1.5)

        return enhanced
    except Exception as e:
        log_error(f"Error taking enhanced screenshot: {e}")
        raise


def enhanced_screenshot_for_failure(region, screenshot=None):
    """Enhanced screenshot specifically optimized for white and yellow text on orange background (backward compatibility)"""
    try:
        if screenshot is None:
            screenshot = take_screenshot()
        cropped = screenshot.crop(region)

        # Resize for better OCR
        cropped = cropped.resize((cropped.width * 2, cropped.height * 2), Image.BICUBIC)

        # Convert to RGB to work with color channels
        cropped = cropped.convert("RGB")

        # Convert to numpy for color processing
        img_np = np.array(cropped)

        # Define orange color range (RGB) - for background
        orange_mask = (
            (img_np[:, :, 0] > 150) &  # High red
            (img_np[:, :, 1] > 80) &   # Medium green
            (img_np[:, :, 2] < 100)    # Low blue
        )

        # Define white text range (RGB) - for "Failure" text
        white_mask = (
            (img_np[:, :, 0] > 200) &  # High red
            (img_np[:, :, 1] > 200) &  # High green
            (img_np[:, :, 2] > 200)    # High blue
        )

        # Define yellow text range (RGB) - for failure rate percentages
        yellow_mask = (
            (img_np[:, :, 0] > 190) &  # High red
            (img_np[:, :, 1] > 140) &  # High green
            (img_np[:, :, 2] < 90)     # Low blue
        )

        # Create a new image: black background, white and yellow text
        result = np.zeros_like(img_np)

        # Set white text (for "Failure")
        result[white_mask] = [255, 255, 255]

        # Set yellow text (for percentages) - convert to white for OCR
        result[yellow_mask] = [255, 255, 255]

        # Set orange background to black
        result[orange_mask] = [0, 0, 0]

        # Convert back to PIL
        pil_img = Image.fromarray(result)

        # Convert to grayscale for OCR
        pil_img = pil_img.convert("L")

        # Enhance contrast for better OCR
        pil_img = ImageEnhance.Contrast(pil_img).enhance(1.5)

        return pil_img
    except Exception as e:
        log_error(f"Error taking failure screenshot: {e}")
        raise


def enhanced_screenshot_for_year(region, screenshot=None):
    """Take a screenshot optimized for year detection (backward compatibility)"""
    try:
        if screenshot is None:
            screenshot = take_screenshot()
        cropped = screenshot.crop(region)

        # Enhance for year text detection
        enhancer = ImageEnhance.Contrast(cropped)
        enhanced = enhancer.enhance(2.5)

        enhancer = ImageEnhance.Sharpness(enhanced)
        enhanced = enhancer.enhance(2.0)

        return enhanced
    except Exception as e:
        log_error(f"Error taking year screenshot: {e}")
        raise


def capture_region(region):
    """Capture a specific region of the screen (backward compatibility)"""
    try:
        screenshot = take_screenshot()
        return screenshot.crop(region)
    except Exception as e:
        log_error(f"Error capturing region: {e}")
        raise
