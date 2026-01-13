"""
Performance Tab for PySide6 GUI
Contains screenshot capture method settings and OCR method settings.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QDoubleSpinBox, QGroupBox, QGridLayout, QFrame, QScrollArea, QLineEdit,
    QPushButton, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

from ..styles import COLORS


class NoScrollSpinBox(QSpinBox):
    """SpinBox that ignores scroll wheel events"""
    def wheelEvent(self, event):
        event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """DoubleSpinBox that ignores scroll wheel events"""
    def wheelEvent(self, event):
        event.ignore()


class EasyOCRInstallThread(QThread):
    """Background thread for EasyOCR GPU installation"""
    progress_signal = Signal(str, int)  # message, percent
    finished_signal = Signal(bool, str)  # success, message
    
    def run(self):
        try:
            from utils.easyocr_installer import install_easyocr_gpu
            success, message = install_easyocr_gpu(
                progress_callback=lambda msg, pct: self.progress_signal.emit(msg, pct)
            )
            self.finished_signal.emit(success, message)
        except Exception as e:
            self.finished_signal.emit(False, f"Installation failed: {str(e)}")


class OCRBenchmarkThread(QThread):
    """Background thread for OCR benchmark"""
    progress_signal = Signal(str, int)  # message, percent
    finished_signal = Signal(object)  # BenchmarkResult
    
    def __init__(self, include_easyocr: bool = False):
        super().__init__()
        self.include_easyocr = include_easyocr
    
    def run(self):
        try:
            from utils.ocr_benchmark import run_ocr_benchmark
            result = run_ocr_benchmark(
                include_easyocr=self.include_easyocr,
                progress_callback=lambda msg, pct: self.progress_signal.emit(msg, pct)
            )
            self.finished_signal.emit(result)
        except Exception as e:
            from utils.ocr_benchmark import BenchmarkResult
            self.finished_signal.emit(BenchmarkResult(
                regions=[], total_tesseract_ms=0, total_easyocr_ms=None,
                screenshot=None, iterations=0, error=str(e)
            ))


class EasyOCRRemoveThread(QThread):
    """Background thread for EasyOCR GPU removal"""
    progress_signal = Signal(str, int)  # message, percent
    finished_signal = Signal(bool, str)  # success, message
    
    def run(self):
        try:
            from utils.easyocr_installer import remove_easyocr_gpu
            success, message = remove_easyocr_gpu(
                progress_callback=lambda msg, pct: self.progress_signal.emit(msg, pct)
            )
            self.finished_signal.emit(success, message)
        except Exception as e:
            self.finished_signal.emit(False, f"Removal failed: {str(e)}")


class PerformanceTab(QScrollArea):
    """Performance configuration tab"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.install_thread = None
        self.benchmark_thread = None
        self.remove_thread = None
        
        self._create_ui()
        self.load_config()
    
    def _create_ui(self):
        """Create performance tab UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # ==================== OCR Method Settings ====================
        ocr_group = QGroupBox("OCR Method")
        ocr_layout = QVBoxLayout(ocr_group)
        ocr_layout.setSpacing(12)
        
        # OCR Method dropdown row
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("OCR Engine:"))
        self.ocr_method_combo = QComboBox()
        self.ocr_method_combo.addItems(["Tesseract (Default)", "EasyOCR GPU"])
        self.ocr_method_combo.currentTextChanged.connect(self._on_ocr_method_change)
        method_row.addWidget(self.ocr_method_combo)
        method_row.addStretch()
        ocr_layout.addLayout(method_row)
        
        # Tesseract benchmark button (visible when Tesseract selected)
        self.tesseract_benchmark_btn = QPushButton("🔬 Run Benchmark")
        self.tesseract_benchmark_btn.setToolTip("Run OCR speed test on current emulator screen (requires Lobby screen)")
        self.tesseract_benchmark_btn.clicked.connect(lambda: self._run_benchmark(include_easyocr=False))
        self.tesseract_benchmark_btn.setVisible(True)  # Visible by default (Tesseract is default)
        ocr_layout.addWidget(self.tesseract_benchmark_btn)
        
        # Status display (hidden by default)
        self.ocr_status_frame = QFrame()
        status_layout = QVBoxLayout(self.ocr_status_frame)
        status_layout.setContentsMargins(0, 8, 0, 0)
        
        # Status label with icon
        self.ocr_status_label = QLabel()
        self.ocr_status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        status_layout.addWidget(self.ocr_status_label)
        
        # GPU info label
        self.gpu_info_label = QLabel()
        self.gpu_info_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        status_layout.addWidget(self.gpu_info_label)
        
        # Install button (hidden by default)
        self.install_btn = QPushButton("Install EasyOCR GPU")
        self.install_btn.setObjectName("accent")
        self.install_btn.clicked.connect(self._install_easyocr_gpu)
        self.install_btn.setVisible(False)
        status_layout.addWidget(self.install_btn)
        
        # Action buttons row (benchmark + remove) - hidden by default
        self.easyocr_actions_frame = QFrame()
        actions_layout = QHBoxLayout(self.easyocr_actions_frame)
        actions_layout.setContentsMargins(0, 8, 0, 0)
        
        self.easyocr_benchmark_btn = QPushButton("🔬 Run Benchmark")
        self.easyocr_benchmark_btn.setToolTip("Compare Tesseract vs EasyOCR GPU speed (requires Lobby screen)")
        self.easyocr_benchmark_btn.clicked.connect(lambda: self._run_benchmark(include_easyocr=True))
        actions_layout.addWidget(self.easyocr_benchmark_btn)
        
        self.easyocr_remove_btn = QPushButton("🗑️ Remove EasyOCR GPU")
        self.easyocr_remove_btn.setToolTip("Remove EasyOCR GPU packages to free disk space (~7-10 GB)")
        self.easyocr_remove_btn.clicked.connect(self._remove_easyocr_gpu)
        actions_layout.addWidget(self.easyocr_remove_btn)
        
        actions_layout.addStretch()
        self.easyocr_actions_frame.setVisible(False)
        status_layout.addWidget(self.easyocr_actions_frame)
        
        # Progress bar (hidden by default)
        self.install_progress = QProgressBar()
        self.install_progress.setVisible(False)
        status_layout.addWidget(self.install_progress)
        
        # Progress message
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        self.progress_label.setVisible(False)
        status_layout.addWidget(self.progress_label)
        
        self.ocr_status_frame.setVisible(False)
        ocr_layout.addWidget(self.ocr_status_frame)
        
        layout.addWidget(ocr_group)
        
        # ==================== Capture Settings ====================
        capture_group = QGroupBox("Screenshot Capture Settings")
        capture_layout = QGridLayout(capture_group)
        capture_layout.setSpacing(12)
        
        capture_layout.addWidget(QLabel("Capture Method:"), 0, 0)
        self.capture_combo = QComboBox()
        self.capture_combo.addItems(["auto", "adb", "nemu_ipc", "ldopengl"])
        self.capture_combo.currentTextChanged.connect(self._on_capture_method_change)
        capture_layout.addWidget(self.capture_combo, 0, 1)
        
        capture_layout.addWidget(QLabel("Screenshot Timeout:"), 1, 0)
        self.timeout_spin = NoScrollSpinBox()
        self.timeout_spin.setRange(1, 30)
        self.timeout_spin.valueChanged.connect(
            lambda v: self._update_adb("screenshot_timeout", v)
        )
        capture_layout.addWidget(self.timeout_spin, 1, 1)
        
        capture_layout.addWidget(QLabel("Input Delay:"), 2, 0)
        self.delay_spin = NoScrollDoubleSpinBox()
        self.delay_spin.setRange(0, 3)
        self.delay_spin.setDecimals(2)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.valueChanged.connect(
            lambda v: self._update_adb("input_delay", v)
        )
        capture_layout.addWidget(self.delay_spin, 2, 1)
        
        layout.addWidget(capture_group)
        
        # NEMU IPC Settings (MuMu Player)
        self.nemu_group = QGroupBox("MuMu Player Settings")
        nemu_layout = QGridLayout(self.nemu_group)
        nemu_layout.setSpacing(12)
        
        nemu_layout.addWidget(QLabel("NEMU Folder:"), 0, 0)
        self.nemu_folder = QLineEdit()
        self.nemu_folder.textChanged.connect(
            lambda v: self._update_nemu("nemu_folder", v)
        )
        nemu_layout.addWidget(self.nemu_folder, 0, 1)
        
        nemu_layout.addWidget(QLabel("Instance ID:"), 1, 0)
        self.nemu_instance = NoScrollSpinBox()
        self.nemu_instance.setRange(0, 10)
        self.nemu_instance.valueChanged.connect(
            lambda v: self._update_nemu("instance_id", v)
        )
        nemu_layout.addWidget(self.nemu_instance, 1, 1)
        
        layout.addWidget(self.nemu_group)
        
        # LDPlayer Settings
        self.ld_group = QGroupBox("LDPlayer Settings")
        ld_layout = QGridLayout(self.ld_group)
        ld_layout.setSpacing(12)
        
        ld_layout.addWidget(QLabel("LD Folder:"), 0, 0)
        self.ld_folder = QLineEdit()
        self.ld_folder.textChanged.connect(
            lambda v: self._update_ld("ld_folder", v)
        )
        ld_layout.addWidget(self.ld_folder, 0, 1)
        
        ld_layout.addWidget(QLabel("Instance ID:"), 1, 0)
        self.ld_instance = NoScrollSpinBox()
        self.ld_instance.setRange(0, 10)
        self.ld_instance.valueChanged.connect(
            lambda v: self._update_ld("instance_id", v)
        )
        ld_layout.addWidget(self.ld_instance, 1, 1)
        
        layout.addWidget(self.ld_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def _on_ocr_method_change(self, value):
        """Handle OCR method change"""
        if "EasyOCR" in value:
            # Show warning dialog first
            result = self._show_easyocr_warning()
            if result != QMessageBox.Yes:
                # User cancelled, revert to Tesseract
                self.ocr_method_combo.blockSignals(True)
                self.ocr_method_combo.setCurrentIndex(0)
                self.ocr_method_combo.blockSignals(False)
                self.ocr_status_frame.setVisible(False)
                return
            
            # Save config
            self.main_window.update_config_value("ocr_backend", "easyocr_gpu")
            
            # Show status frame and check EasyOCR status
            self.ocr_status_frame.setVisible(True)
            self.tesseract_benchmark_btn.setVisible(False)  # Hide tesseract benchmark
            self._check_easyocr_status()
        else:
            # Tesseract selected
            self.main_window.update_config_value("ocr_backend", "tesseract")
            self.ocr_status_frame.setVisible(False)
            self.tesseract_benchmark_btn.setVisible(True)  # Show tesseract benchmark
    
    def _show_easyocr_warning(self) -> int:
        """Show EasyOCR GPU warning dialog"""
        msg = QMessageBox(self)
        msg.setWindowTitle("EasyOCR GPU Acceleration")
        msg.setIcon(QMessageBox.Information)
        msg.setTextFormat(Qt.RichText)
        msg.setText(
            "<p style='font-size: 14px;'><b>⚡ EasyOCR GPU Acceleration</b></p>"
            "<p>EasyOCR provides significantly faster OCR performance using your GPU.</p>"
            "<p><b>Requirements:</b><br>"
            "• NVIDIA GPU"
            "• RTX 30xx or higher for best performance"
            "<p><b>Note:</b><br>"
            "• First-time setup will download approximately <b>7 GB</b> of data<br>"
            "• This includes PyTorch CUDA and EasyOCR models<br>"
            "• Please note that this will increase UMAT size <b>up to 10GB</b>, which might become a problem for some users<br>"
            "• Installation may take several minutes</p>"
            "<p>Do you want to continue?</p>"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        return msg.exec()
    
    def _check_easyocr_status(self):
        """Check and display EasyOCR GPU status"""
        try:
            from utils.easyocr_installer import check_easyocr_gpu_ready
            status = check_easyocr_gpu_ready()
            
            if status['ready']:
                # EasyOCR GPU is ready
                self.ocr_status_label.setText("✓ EasyOCR GPU is ready")
                self.ocr_status_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-weight: bold;")
                self.gpu_info_label.setText(f"GPU: {status['gpu_name']} • CUDA {status['cuda_version']}")
                self.gpu_info_label.setVisible(True)
                self.install_btn.setVisible(False)
                self.easyocr_actions_frame.setVisible(True)  # Show benchmark + remove buttons
            else:
                # EasyOCR GPU not ready
                self.ocr_status_label.setText(f"✗ {status['error']}")
                self.ocr_status_label.setStyleSheet(f"color: {COLORS['accent_orange']};")
                self.easyocr_actions_frame.setVisible(False)  # Hide action buttons
                
                if status['gpu_name']:
                    self.gpu_info_label.setText(f"GPU detected: {status['gpu_name']}")
                    self.gpu_info_label.setVisible(True)
                    self.install_btn.setVisible(True)
                else:
                    self.gpu_info_label.setText("No NVIDIA GPU detected. EasyOCR GPU requires an NVIDIA GPU with CUDA support.")
                    self.gpu_info_label.setVisible(True)
                    self.install_btn.setVisible(False)
                    
        except Exception as e:
            self.ocr_status_label.setText(f"✗ Error checking status: {str(e)}")
            self.ocr_status_label.setStyleSheet(f"color: {COLORS['accent_red']};")
            self.gpu_info_label.setVisible(False)
            self.install_btn.setVisible(False)
            self.easyocr_actions_frame.setVisible(False)
    
    def _install_easyocr_gpu(self):
        """Start EasyOCR GPU installation in background thread"""
        self.install_btn.setEnabled(False)
        self.install_btn.setText("Installing...")
        self.install_progress.setVisible(True)
        self.install_progress.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting installation...")
        
        self.install_thread = EasyOCRInstallThread()
        self.install_thread.progress_signal.connect(self._on_install_progress)
        self.install_thread.finished_signal.connect(self._on_install_finished)
        self.install_thread.start()
    
    def _on_install_progress(self, message: str, percent: int):
        """Handle installation progress update"""
        self.install_progress.setValue(percent)
        self.progress_label.setText(message)
    
    def _on_install_finished(self, success: bool, message: str):
        """Handle installation completion"""
        self.install_progress.setVisible(False)
        self.progress_label.setVisible(False)
        self.install_btn.setEnabled(True)
        self.install_btn.setText("Install EasyOCR GPU")
        
        if success:
            QMessageBox.information(
                self, "Installation Complete",
                f"✓ {message}\n\nEasyOCR GPU is now ready to use."
            )
            self._check_easyocr_status()  # Refresh status
        else:
            QMessageBox.warning(
                self, "Installation Failed",
                f"✗ {message}\n\nPlease check the requirements and try again."
            )
            self._check_easyocr_status()  # Refresh status
    
    def _run_benchmark(self, include_easyocr: bool = False):
        """Start OCR benchmark in background thread"""
        # Show warning first
        result = QMessageBox.information(
            self, "OCR Benchmark",
            "⚠️ Please ensure:\n\n"
            "• The emulator is running\n"
            "• The game is on the Lobby screen\n\n"
            "The benchmark will capture the current screen and test OCR performance.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Disable buttons during benchmark
        self.tesseract_benchmark_btn.setEnabled(False)
        self.easyocr_benchmark_btn.setEnabled(False)
        self.install_progress.setVisible(True)
        self.install_progress.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting benchmark...")
        
        self.benchmark_thread = OCRBenchmarkThread(include_easyocr=include_easyocr)
        self.benchmark_thread.progress_signal.connect(self._on_benchmark_progress)
        self.benchmark_thread.finished_signal.connect(self._on_benchmark_finished)
        self.benchmark_thread.start()
    
    def _on_benchmark_progress(self, message: str, percent: int):
        """Handle benchmark progress update"""
        self.install_progress.setValue(percent)
        self.progress_label.setText(message)
    
    def _on_benchmark_finished(self, result):
        """Handle benchmark completion"""
        self.install_progress.setVisible(False)
        self.progress_label.setVisible(False)
        self.tesseract_benchmark_btn.setEnabled(True)
        self.easyocr_benchmark_btn.setEnabled(True)
        
        if result.error:
            QMessageBox.warning(
                self, "Benchmark Failed",
                f"✗ {result.error}\n\nMake sure the emulator is connected and try again."
            )
            return
        
        # Build results table
        lines = ["OCR Benchmark Results", "=" * 50, ""]
        lines.append(f"Iterations: {result.iterations}")
        lines.append("")
        
        if result.total_easyocr_ms:
            # Comparison mode
            lines.append(f"{'Region':<15} {'Tesseract':>12} {'EasyOCR':>12} {'Speedup':>10}")
            lines.append("-" * 50)
            
            for r in result.regions:
                speedup = f"{r.speedup:.2f}x" if r.speedup else "N/A"
                lines.append(
                    f"{r.region_name:<15} {r.tesseract_time_ms:>10.2f}ms "
                    f"{r.easyocr_time_ms:>10.2f}ms {speedup:>10}"
                )
            
            lines.append("-" * 50)
            overall = result.overall_speedup
            lines.append(
                f"{'TOTAL':<15} {result.total_tesseract_ms:>10.2f}ms "
                f"{result.total_easyocr_ms:>10.2f}ms {overall:.2f}x"
            )
            lines.append("")
            if overall and overall > 1:
                lines.append(f"✓ EasyOCR GPU is {overall:.1f}x faster than Tesseract")
            else:
                lines.append(f"✗ Tesseract is faster in this test")
        else:
            # Tesseract-only mode
            lines.append(f"{'Region':<20} {'Time':>15}")
            lines.append("-" * 40)
            
            for r in result.regions:
                lines.append(f"{r.region_name:<20} {r.tesseract_time_ms:>12.2f}ms")
            
            lines.append("-" * 40)
            lines.append(f"{'TOTAL':<20} {result.total_tesseract_ms:>12.2f}ms")
        
        QMessageBox.information(
            self, "Benchmark Results",
            "\n".join(lines)
        )
    
    def _remove_easyocr_gpu(self):
        """Start EasyOCR GPU removal in background thread"""
        try:
            from utils.easyocr_installer import get_easyocr_disk_usage
            disk_usage = get_easyocr_disk_usage()
        except:
            disk_usage = 7.5
        
        result = QMessageBox.warning(
            self, "Remove EasyOCR GPU",
            f"⚠️ This will remove the following packages:\n\n"
            f"• torch\n• torchvision\n• torchaudio\n• easyocr\n\n"
            f"Estimated disk space to be freed: ~{disk_usage:.1f} GB\n\n"
            f"You can reinstall EasyOCR GPU later if needed.\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Update config to use Tesseract
        self.main_window.update_config_value("ocr_backend", "tesseract")
        
        # Disable buttons during removal
        self.easyocr_benchmark_btn.setEnabled(False)
        self.easyocr_remove_btn.setEnabled(False)
        self.install_progress.setVisible(True)
        self.install_progress.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting removal...")
        
        self.remove_thread = EasyOCRRemoveThread()
        self.remove_thread.progress_signal.connect(self._on_remove_progress)
        self.remove_thread.finished_signal.connect(self._on_remove_finished)
        self.remove_thread.start()
    
    def _on_remove_progress(self, message: str, percent: int):
        """Handle removal progress update"""
        self.install_progress.setValue(percent)
        self.progress_label.setText(message)
    
    def _on_remove_finished(self, success: bool, message: str):
        """Handle removal completion"""
        self.install_progress.setVisible(False)
        self.progress_label.setVisible(False)
        self.easyocr_benchmark_btn.setEnabled(True)
        self.easyocr_remove_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(
                self, "Removal Complete",
                f"✓ {message}\n\nDisk space has been freed. "
                f"OCR backend has been switched to Tesseract."
            )
            # Switch to Tesseract in UI
            self.ocr_method_combo.blockSignals(True)
            self.ocr_method_combo.setCurrentIndex(0)
            self.ocr_method_combo.blockSignals(False)
            self.ocr_status_frame.setVisible(False)
            self.tesseract_benchmark_btn.setVisible(True)
        else:
            QMessageBox.warning(
                self, "Removal Failed",
                f"✗ {message}\n\nSome packages may not have been removed."
            )
        
        self._check_easyocr_status()  # Refresh status
    
    def _on_capture_method_change(self, value):
        """Handle capture method change"""
        self.main_window.update_config_value("capture_method", value)
        self._update_emulator_settings_visibility()
    
    def _update_emulator_settings_visibility(self):
        """Show/hide emulator-specific settings based on capture method"""
        method = self.capture_combo.currentText()
        
        # Show MuMu settings only for nemu_ipc
        self.nemu_group.setVisible(method == "nemu_ipc")
        
        # Show LDPlayer settings only for ldopengl
        self.ld_group.setVisible(method == "ldopengl")
    
    def load_config(self):
        """Load config values"""
        config = self.main_window.get_config()
        
        # OCR backend - block signals to prevent triggering warning dialog
        self.ocr_method_combo.blockSignals(True)
        ocr_backend = config.get("ocr_backend", "tesseract")
        if ocr_backend == "easyocr_gpu":
            self.ocr_method_combo.setCurrentIndex(1)
            self.ocr_status_frame.setVisible(True)
            self.tesseract_benchmark_btn.setVisible(False)
            self._check_easyocr_status()
        else:
            self.ocr_method_combo.setCurrentIndex(0)
            self.ocr_status_frame.setVisible(False)
            self.tesseract_benchmark_btn.setVisible(True)
        self.ocr_method_combo.blockSignals(False)
        
        self.capture_combo.setCurrentText(config.get("capture_method", "auto"))
        
        adb = config.get("adb_config", {})
        self.timeout_spin.setValue(adb.get("screenshot_timeout", 5))
        self.delay_spin.setValue(adb.get("input_delay", 0.5))
        
        nemu = config.get("nemu_ipc_config", {})
        self.nemu_folder.setText(nemu.get("nemu_folder", ""))
        self.nemu_instance.setValue(nemu.get("instance_id", 0))
        
        ld = config.get("ldopengl_config", {})
        self.ld_folder.setText(ld.get("ld_folder", ""))
        self.ld_instance.setValue(ld.get("instance_id", 0))
        
        # Update visibility after loading
        self._update_emulator_settings_visibility()
    
    def _update_adb(self, key, value):
        self.main_window.update_nested_config_value("adb_config", key, value)
    
    def _update_nemu(self, key, value):
        self.main_window.update_nested_config_value("nemu_ipc_config", key, value)
    
    def _update_ld(self, key, value):
        self.main_window.update_nested_config_value("ldopengl_config", key, value)


