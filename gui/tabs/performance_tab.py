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


class PerformanceTab(QScrollArea):
    """Performance configuration tab"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.install_thread = None
        
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
            self._check_easyocr_status()
        else:
            # Tesseract selected
            self.main_window.update_config_value("ocr_backend", "tesseract")
            self.ocr_status_frame.setVisible(False)
    
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
            "• NVIDIA GPU (GTX 1060 or higher recommended)<br>"
            "• RTX 30xx or higher for best performance<br>"
            "• CUDA drivers installed on your system</p>"
            "<p><b>Note:</b><br>"
            "• First-time setup will download approximately <b>2.5 GB</b> of data<br>"
            "• This includes PyTorch CUDA and EasyOCR models<br>"
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
            else:
                # EasyOCR GPU not ready
                self.ocr_status_label.setText(f"✗ {status['error']}")
                self.ocr_status_label.setStyleSheet(f"color: {COLORS['accent_orange']};")
                
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
            self._check_easyocr_status()
        else:
            self.ocr_method_combo.setCurrentIndex(0)
            self.ocr_status_frame.setVisible(False)
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


