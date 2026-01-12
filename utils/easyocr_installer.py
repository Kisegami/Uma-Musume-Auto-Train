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
from ctypes import c_int, c_void_p, byref, c_uint, c_ulonglong
from typing import Tuple, Optional, Dict, Callable

# NVML Constants
NVML_SUCCESS = 0
NVML_DEVICE_NAME_BUFFER_SIZE = 64
NVML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE = 80


def _load_nvml():
    """Load NVIDIA Management Library using ctypes."""
    try:
        if platform.system() == "Windows":
            try:
                nvml = ctypes.windll.LoadLibrary("nvml.dll")
            except OSError:
                # Alternative location
                nvml = ctypes.cdll.LoadLibrary(
                    "C:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvml.dll"
                )
        else:
            # Linux/Mac
            nvml = ctypes.CDLL("libnvidia-ml.so.1")
        return nvml
    except Exception:
        return None


def get_gpu_info() -> Tuple[Optional[str], Optional[float]]:
    """
    Get GPU name and memory using NVML.
    
    Returns:
        Tuple of (gpu_name, memory_gb) or (None, None) if not available
    """
    nvml = _load_nvml()
    if not nvml:
        return None, None
    
    try:
        result = nvml.nvmlInit_v2()
        if result != NVML_SUCCESS:
            return None, None
        
        # Get device count
        device_count = c_uint()
        result = nvml.nvmlDeviceGetCount_v2(byref(device_count))
        if result != NVML_SUCCESS or device_count.value == 0:
            nvml.nvmlShutdown()
            return None, None
        
        # Get first GPU info
        handle = c_void_p()
        result = nvml.nvmlDeviceGetHandleByIndex_v2(c_uint(0), byref(handle))
        if result != NVML_SUCCESS:
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
        
    except Exception:
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
    nvml = _load_nvml()
    if not nvml:
        return None
    
    try:
        result = nvml.nvmlInit_v2()
        if result != NVML_SUCCESS:
            return None
        
        cuda_version = c_int()
        result = nvml.nvmlSystemGetCudaDriverVersion(byref(cuda_version))
        
        if result == NVML_SUCCESS:
            version_num = cuda_version.value
            major = version_num // 1000
            minor = (version_num % 1000) // 10
            nvml.nvmlShutdown()
            return f"{major}.{minor}"
        
        nvml.nvmlShutdown()
        return None
        
    except Exception:
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
            'error': str or None
        }
    """
    result = {
        'ready': False,
        'gpu_name': None,
        'gpu_memory_gb': None,
        'cuda_version': None,
        'pytorch_cuda': None,
        'easyocr_installed': False,
        'error': None
    }
    
    # Check GPU
    gpu_name, gpu_memory = get_gpu_info()
    result['gpu_name'] = gpu_name
    result['gpu_memory_gb'] = gpu_memory
    
    if not gpu_name:
        result['error'] = "No NVIDIA GPU detected"
        return result
    
    # Check CUDA version
    cuda_version = get_cuda_version()
    result['cuda_version'] = cuda_version
    
    if not cuda_version:
        result['error'] = "CUDA driver not detected"
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
            return False, "No NVIDIA GPU detected. EasyOCR GPU requires an NVIDIA GPU."
        
        report(f"Found GPU: {gpu_name}", 10)
        
        # Step 2: Get CUDA version
        report("Detecting CUDA version...", 15)
        cuda_version = get_cuda_version()
        
        if not cuda_version:
            return False, "CUDA driver not detected. Please install NVIDIA drivers with CUDA support."
        
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
        
        # Step 7: Verify installation
        report("Verifying installation...", 95)
        
        # Need to reload torch module after installation
        import importlib
        if 'torch' in sys.modules:
            del sys.modules['torch']
        
        try:
            import torch
            if not torch.cuda.is_available():
                return False, "PyTorch installed but CUDA not available. Check CUDA drivers."
            
            import easyocr
            report("Installation complete!", 100)
            return True, f"EasyOCR GPU installed successfully. Using {gpu_name} with CUDA {cuda_version}"
            
        except ImportError as e:
            return False, f"Installation verification failed: {e}"
        
    except Exception as e:
        return False, f"Installation failed: {str(e)}"


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
