"""
EasyOCR GPU Installer Utility
Handles GPU detection, CUDA version detection, and EasyOCR installation.
Uses only Python standard library for GPU detection (ctypes for NVML).
"""

import sys
import os
import subprocess
import ctypes
import platform
import traceback
from ctypes import c_int, c_void_p, byref, c_uint, c_ulonglong
from typing import Tuple, Optional, Dict, Callable

# NVML Constants
NVML_SUCCESS = 0
NVML_DEVICE_NAME_BUFFER_SIZE = 64
NVML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE = 80


# Store last error details for diagnostic purposes
_last_nvml_error: Optional[str] = None


def _load_nvml():
    """Load NVIDIA Management Library using ctypes.
    
    Returns:
        The NVML library object, or None if loading failed.
        Sets _last_nvml_error with detailed error info on failure.
    """
    global _last_nvml_error
    _last_nvml_error = None
    
    try:
        if platform.system() == "Windows":
            try:
                nvml = ctypes.windll.LoadLibrary("nvml.dll")
            except OSError as e1:
                # Alternative location
                try:
                    nvml = ctypes.cdll.LoadLibrary(
                        "C:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvml.dll"
                    )
                except OSError as e2:
                    _last_nvml_error = (
                        f"Failed to load NVIDIA Management Library (nvml.dll).\n\n"
                        f"Primary attempt: {e1}\n"
                        f"Fallback attempt (NVSMI path): {e2}\n\n"
                        f"This usually means:\n"
                        f"  • NVIDIA GPU drivers are not installed\n"
                        f"  • NVIDIA drivers are corrupted or outdated\n"
                        f"  • A required DLL dependency is missing\n\n"
                        f"Try reinstalling NVIDIA GPU drivers from:\n"
                        f"https://www.nvidia.com/Download/index.aspx"
                    )
                    return None
        else:
            # Linux/Mac
            nvml = ctypes.CDLL("libnvidia-ml.so.1")
        return nvml
    except Exception as e:
        _last_nvml_error = (
            f"Failed to load NVIDIA Management Library: {type(e).__name__}: {e}\n\n"
            f"Traceback:\n{traceback.format_exc()}"
        )
        return None


def get_gpu_info() -> Tuple[Optional[str], Optional[float]]:
    """
    Get GPU name and memory using NVML.
    
    Returns:
        Tuple of (gpu_name, memory_gb) or (None, None) if not available
    """
    global _last_nvml_error
    nvml = _load_nvml()
    if not nvml:
        return None, None
    
    try:
        result = nvml.nvmlInit_v2()
        if result != NVML_SUCCESS:
            _last_nvml_error = f"NVML initialization failed with error code: {result}"
            return None, None
        
        # Get device count
        device_count = c_uint()
        result = nvml.nvmlDeviceGetCount_v2(byref(device_count))
        if result != NVML_SUCCESS or device_count.value == 0:
            _last_nvml_error = f"No GPU devices found (NVML error code: {result}, device count: {device_count.value})"
            nvml.nvmlShutdown()
            return None, None
        
        # Get first GPU info
        handle = c_void_p()
        result = nvml.nvmlDeviceGetHandleByIndex_v2(c_uint(0), byref(handle))
        if result != NVML_SUCCESS:
            _last_nvml_error = f"Failed to get GPU handle (NVML error code: {result})"
            nvml.nvmlShutdown()
            return None, None
        
        # Get device name
        name = ctypes.create_string_buffer(NVML_DEVICE_NAME_BUFFER_SIZE)
        result = nvml.nvmlDeviceGetName(handle, name, c_uint(NVML_DEVICE_NAME_BUFFER_SIZE))
        gpu_name = name.value.decode('utf-8') if result == NVML_SUCCESS else None
        
        # Get memory info
        class MemoryInfo(ctypes.Structure):
            _fields_ = [
                ("total", c_ulonglong),
                ("free", c_ulonglong),
                ("used", c_ulonglong)
            ]
        
        memory = MemoryInfo()
        result = nvml.nvmlDeviceGetMemoryInfo(handle, byref(memory))
        memory_gb = memory.total / (1024**3) if result == NVML_SUCCESS else None
        
        nvml.nvmlShutdown()
        return gpu_name, memory_gb
        
    except Exception as e:
        _last_nvml_error = f"GPU detection error: {type(e).__name__}: {e}\n\nTraceback:\n{traceback.format_exc()}"
        try:
            nvml.nvmlShutdown()
        except:
            pass
        return None, None


def get_cuda_version() -> Optional[str]:
    """
    Get CUDA driver version using NVML.
    
    Returns:
        CUDA version string (e.g., "12.4") or None if not available
    """
    global _last_nvml_error
    nvml = _load_nvml()
    if not nvml:
        return None
    
    try:
        result = nvml.nvmlInit_v2()
        if result != NVML_SUCCESS:
            _last_nvml_error = f"NVML init failed for CUDA version check (error code: {result})"
            return None
        
        cuda_version = c_int()
        result = nvml.nvmlSystemGetCudaDriverVersion(byref(cuda_version))
        
        if result == NVML_SUCCESS:
            version_num = cuda_version.value
            major = version_num // 1000
            minor = (version_num % 1000) // 10
            nvml.nvmlShutdown()
            return f"{major}.{minor}"
        
        _last_nvml_error = f"Failed to get CUDA version (NVML error code: {result})"
        nvml.nvmlShutdown()
        return None
        
    except Exception as e:
        _last_nvml_error = f"CUDA version detection error: {type(e).__name__}: {e}\n\nTraceback:\n{traceback.format_exc()}"
        try:
            nvml.nvmlShutdown()
        except:
            pass
        return None


def check_pytorch_cuda_available() -> Tuple[bool, Optional[str]]:
    """
    Check if PyTorch with CUDA support is installed.
    
    Returns:
        Tuple of (is_available, cuda_version_in_pytorch)
    """
    try:
        import torch
        if torch.cuda.is_available():
            cuda_version = torch.version.cuda
            return True, cuda_version
        return False, None
    except ImportError:
        return False, None


def check_easyocr_installed() -> bool:
    """Check if EasyOCR is installed."""
    try:
        import easyocr
        return True
    except ImportError:
        return False


def get_last_nvml_error() -> Optional[str]:
    """Get the last NVML error detail string, if any."""
    return _last_nvml_error


def check_easyocr_gpu_ready() -> Dict:
    """
    Check if EasyOCR GPU is ready to use.
    
    Returns:
        Dict with status information:
        {
            'ready': bool,
            'gpu_name': str or None,
            'gpu_memory_gb': float or None,
            'cuda_version': str or None,
            'pytorch_cuda': str or None,
            'easyocr_installed': bool,
            'error': str or None,
            'error_detail': str or None
        }
    """
    result = {
        'ready': False,
        'gpu_name': None,
        'gpu_memory_gb': None,
        'cuda_version': None,
        'pytorch_cuda': None,
        'easyocr_installed': False,
        'error': None,
        'error_detail': None
    }
    
    # Check GPU
    gpu_name, gpu_memory = get_gpu_info()
    result['gpu_name'] = gpu_name
    result['gpu_memory_gb'] = gpu_memory
    
    if not gpu_name:
        result['error'] = "No NVIDIA GPU detected"
        result['error_detail'] = get_last_nvml_error()
        return result
    
    # Check CUDA version
    cuda_version = get_cuda_version()
    result['cuda_version'] = cuda_version
    
    if not cuda_version:
        result['error'] = "CUDA driver not detected"
        result['error_detail'] = get_last_nvml_error()
        return result
    
    # Check PyTorch CUDA
    pytorch_available, pytorch_cuda = check_pytorch_cuda_available()
    result['pytorch_cuda'] = pytorch_cuda
    
    if not pytorch_available:
        result['error'] = "PyTorch with CUDA not installed"
        return result
    
    # Check EasyOCR
    easyocr_installed = check_easyocr_installed()
    result['easyocr_installed'] = easyocr_installed
    
    if not easyocr_installed:
        result['error'] = "EasyOCR not installed"
        return result
    
    # All checks passed
    result['ready'] = True
    result['error'] = None
    return result


def get_pytorch_cuda_index(cuda_version: str) -> str:
    """
    Get PyTorch CUDA index URL suffix for given CUDA version.
    
    Simply removes the dot from CUDA version (e.g., "12.4" -> "cu124").
    For CUDA > 12.9, caps at cu129 since PyTorch 2.8.0 only supports up to CUDA 12.9.
    
    Args:
        cuda_version: CUDA version string (e.g., "13.0", "12.4")
    
    Returns:
        PyTorch CUDA suffix (e.g., "cu129", "cu124")
    """
    try:
        parts = cuda_version.split('.')
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        
        # PyTorch 2.8.0 supports up to CUDA 12.9
        # For CUDA > 12.9, cap at cu129
        if major > 12 or (major == 12 and minor > 9):
            return "cu129"
        
        # Otherwise just remove the dot
        cuda_suffix = cuda_version.replace('.', '')
        return f"cu{cuda_suffix}"
    except Exception:
        return "cu129"  # Safe default


def install_easyocr_gpu(
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Tuple[bool, str]:
    """
    Install EasyOCR with GPU support (PyTorch CUDA + EasyOCR).
    
    Args:
        progress_callback: Optional callback(message, percent) for progress updates
    
    Returns:
        Tuple of (success, message)
    """
    def report(msg: str, pct: int):
        if progress_callback:
            progress_callback(msg, pct)
    
    try:
        # Step 1: Check GPU
        report("Detecting GPU...", 5)
        gpu_name, gpu_memory = get_gpu_info()
        
        if not gpu_name:
            detail = get_last_nvml_error()
            msg = "No NVIDIA GPU detected. EasyOCR GPU requires an NVIDIA GPU."
            if detail:
                msg += f"\n\nDetailed error:\n{detail}"
            return False, msg
        
        report(f"Found GPU: {gpu_name}", 10)
        
        # Step 2: Get CUDA version
        report("Detecting CUDA version...", 15)
        cuda_version = get_cuda_version()
        
        if not cuda_version:
            detail = get_last_nvml_error()
            msg = "CUDA driver not detected. Please install NVIDIA drivers with CUDA support."
            if detail:
                msg += f"\n\nDetailed error:\n{detail}"
            return False, msg
        
        report(f"CUDA version: {cuda_version}", 20)
        
        # Step 3: Determine PyTorch CUDA version
        pytorch_cuda = get_pytorch_cuda_index(cuda_version)
        report(f"Using PyTorch CUDA: {pytorch_cuda}", 25)
        
        # Step 4: Uninstall existing PyTorch (if CPU-only)
        report("Checking existing PyTorch installation...", 30)
        try:
            import torch
            if not torch.cuda.is_available():
                report("Removing CPU-only PyTorch...", 35)
                subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", "-y", 
                     "torch", "torchvision", "torchaudio"],
                    capture_output=True,
                    check=False
                )
        except ImportError:
            pass
        
        # Step 5: Install PyTorch with CUDA
        report(f"Installing PyTorch with CUDA ({pytorch_cuda})...", 40)
        report("Downloading PyTorch (this may take several minutes)...", 42)
        
        pytorch_url = f"https://download.pytorch.org/whl/{pytorch_cuda}"
        
        # Use Popen for real-time output streaming
        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "install",
             "torch==2.8.0", "torchvision", "torchaudio",
             "--index-url", pytorch_url, "--progress-bar", "on"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output and update progress
        pytorch_progress = 42
        last_line = ""
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                last_line = line
                # Parse download progress from pip output
                if "Downloading" in line:
                    # Extract package name
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "Downloading" in part and i + 1 < len(parts):
                            pkg_name = parts[i + 1].split('/')[-1][:40]
                            report(f"Downloading: {pkg_name}", pytorch_progress)
                            break
                elif "%" in line:
                    # Try to extract percentage
                    try:
                        import re
                        match = re.search(r'(\d+)%', line)
                        if match:
                            pct = int(match.group(1))
                            # Map 0-100% to 42-68% range
                            mapped_pct = 42 + int(pct * 0.26)
                            report(f"Downloading: {pct}%", mapped_pct)
                    except:
                        pass
                elif "Installing" in line or "Successfully" in line:
                    report(line[:60], 65)
        
        process.wait()
        
        if process.returncode != 0:
            return False, f"Failed to install PyTorch: {last_line}"
        
        report("PyTorch installed successfully", 70)
        
        # Step 6: Install EasyOCR
        report("Installing EasyOCR...", 72)
        
        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "easyocr"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                last_line = line
                if "Downloading" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "Downloading" in part and i + 1 < len(parts):
                            pkg_name = parts[i + 1].split('/')[-1][:40]
                            report(f"Downloading: {pkg_name}", 75)
                            break
                elif "Installing" in line or "Successfully" in line:
                    report(line[:60], 85)
        
        process.wait()
        
        if process.returncode != 0:
            return False, f"Failed to install EasyOCR: {last_line}"
        
        report("EasyOCR installed successfully", 90)
        
        # Step 7: Verify installation in a subprocess
        # PyTorch C extensions cannot be safely re-imported in the same process,
        # so we verify in a fresh subprocess to avoid the '_has_torch_function' error.
        report("Verifying installation...", 95)
        
        verify_script = (
            "import sys; "
            "import torch; "
            "cuda_ok = torch.cuda.is_available(); "
            "import easyocr; "
            "print('CUDA_OK' if cuda_ok else 'CUDA_FAIL')"
        )
        
        try:
            verify_result = subprocess.run(
                [sys.executable, "-c", verify_script],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if verify_result.returncode != 0:
                stderr = verify_result.stderr.strip()
                return False, f"Installation verification failed:\n{stderr}"
            
            output = verify_result.stdout.strip()
            if "CUDA_FAIL" in output:
                return False, "PyTorch installed but CUDA not available. Check CUDA drivers."
            
            if "CUDA_OK" not in output:
                return False, f"Unexpected verification output: {output}"
            
            report("Installation complete!", 100)
            return True, f"EasyOCR GPU installed successfully. Using {gpu_name} with CUDA {cuda_version}"
            
        except subprocess.TimeoutExpired:
            return False, "Installation verification timed out (120s). Installation may still be OK — try restarting."
        except Exception as e:
            return False, f"Installation verification failed: {e}"
        
    except Exception as e:
        detail = traceback.format_exc()
        return False, f"Installation failed: {str(e)}\n\nFull traceback:\n{detail}"


def test_easyocr_gpu() -> Tuple[bool, str]:
    """
    Test EasyOCR GPU by initializing the reader.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        import easyocr
        import numpy as np
        
        # Initialize reader with GPU
        reader = easyocr.Reader(['en'], gpu=True)
        
        # Test with a simple image
        test_img = np.ones((100, 300, 3), dtype=np.uint8) * 255
        results = reader.readtext(test_img)
        
        return True, "EasyOCR GPU is working correctly"
        
    except Exception as e:
        return False, f"EasyOCR GPU test failed: {str(e)}"


def get_easyocr_disk_usage() -> float:
    """
    Get approximate disk space used by EasyOCR + PyTorch CUDA packages.
    
    Returns:
        Estimated disk usage in GB
    """
    try:
        import importlib.metadata
        
        packages = ['torch', 'torchvision', 'torchaudio', 'easyocr']
        total_size = 0
        
        for pkg in packages:
            try:
                dist = importlib.metadata.distribution(pkg)
                # Get package location and estimate size
                if dist.files:
                    for file in dist.files:
                        try:
                            total_size += file.size if hasattr(file, 'size') and file.size else 0
                        except:
                            pass
            except importlib.metadata.PackageNotFoundError:
                pass
        
        # If we couldn't get actual sizes, return estimate
        if total_size == 0:
            # Check if torch with CUDA is installed
            try:
                import torch
                if torch.cuda.is_available():
                    return 7.5  # Typical size for PyTorch CUDA + EasyOCR
                return 2.0  # CPU-only PyTorch
            except ImportError:
                return 0.0
        
        return total_size / (1024 ** 3)  # Convert to GB
        
    except Exception:
        return 7.5  # Safe estimate


def remove_easyocr_gpu(
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Tuple[bool, str]:
    """
    Remove EasyOCR GPU packages (torch, torchvision, torchaudio, easyocr).
    
    Args:
        progress_callback: Optional callback(message, percent) for progress updates
    
    Returns:
        Tuple of (success, message)
    """
    def report(msg: str, pct: int):
        if progress_callback:
            progress_callback(msg, pct)
    
    packages_to_remove = ['easyocr', 'torch', 'torchvision', 'torchaudio']
    removed_packages = []
    failed_packages = []
    
    try:
        report("Checking installed packages...", 5)
        
        # Check which packages are installed
        installed = []
        for pkg in packages_to_remove:
            try:
                __import__(pkg.replace('-', '_'))
                installed.append(pkg)
            except ImportError:
                pass
        
        if not installed:
            return True, "No EasyOCR GPU packages found to remove"
        
        report(f"Found {len(installed)} packages to remove", 10)
        
        # Clear module cache before uninstalling
        report("Clearing module cache...", 15)
        import sys
        modules_to_clear = [m for m in sys.modules.keys() 
                          if any(pkg in m for pkg in packages_to_remove)]
        for mod in modules_to_clear:
            try:
                del sys.modules[mod]
            except:
                pass
        
        # Uninstall packages
        total_packages = len(installed)
        for idx, pkg in enumerate(installed):
            progress = 20 + int((idx / total_packages) * 70)
            report(f"Removing {pkg}...", progress)
            
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", "-y", pkg],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    removed_packages.append(pkg)
                else:
                    failed_packages.append(pkg)
                    
            except subprocess.TimeoutExpired:
                failed_packages.append(pkg)
            except Exception as e:
                failed_packages.append(pkg)
        
        report("Cleanup complete!", 100)
        
        if failed_packages:
            return False, f"Removed: {', '.join(removed_packages)}. Failed: {', '.join(failed_packages)}"
        
        return True, f"Successfully removed: {', '.join(removed_packages)}"
        
    except Exception as e:
        return False, f"Removal failed: {str(e)}"
