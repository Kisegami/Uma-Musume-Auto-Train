"""
Main Tab for PySide6 GUI
Contains ADB configuration and mode settings.
"""

import os
from urllib.parse import urlparse, urlunparse
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QGroupBox, QGridLayout, QFrame, QScrollArea, QMessageBox,
    QSizePolicy, QCheckBox, QSpinBox, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from ..styles import COLORS


class MainTab(QScrollArea):
    """Main configuration tab"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self._create_ui()
        self.load_config()
    
    def _create_ui(self):
        """Create main tab UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Mode Configuration
        mode_group = QGroupBox("Mode Configuration")
        mode_main_layout = QHBoxLayout(mode_group)
        mode_main_layout.setSpacing(16)
        mode_main_layout.setContentsMargins(12, 6, 12, 6)
        
        # Left side: Settings
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(6)
        
        # Game Mode row
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_row.addWidget(QLabel("Game Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["URA Finale", "Unity Cup", "Trackblazer"])
        self.mode_combo.setFixedWidth(140)
        self.mode_combo.currentTextChanged.connect(self._on_mode_change)
        mode_row.addWidget(self.mode_combo)
        settings_layout.addLayout(mode_row)
        
        # Unity Team row (only visible when Unity mode selected)
        self.unity_team_row = QWidget()
        team_row_layout = QHBoxLayout(self.unity_team_row)
        team_row_layout.setContentsMargins(0, 0, 0, 0)
        team_row_layout.setSpacing(8)
        self.unity_team_label = QLabel("Unity Team:")
        team_row_layout.addWidget(self.unity_team_label)
        self.unity_team_combo = QComboBox()
        self.unity_team_combo.addItems([
            "Happy Hoppers", "Sunny Runners", "Carrot Pudding", 
            "Blue Bloom", "Team Carrot"
        ])
        self.unity_team_combo.setFixedWidth(140)
        self.unity_team_combo.currentTextChanged.connect(self._on_unity_team_change)
        team_row_layout.addWidget(self.unity_team_combo)
        settings_layout.addWidget(self.unity_team_row)
        
        # Wrap settings in container with top alignment
        settings_container = QWidget()
        settings_container.setLayout(settings_layout)
        mode_main_layout.addWidget(settings_container, alignment=Qt.AlignTop)
        mode_main_layout.addStretch()
        
        # Right side: Scenario Logo (aligned to top)
        self.scenario_logo = QLabel()
        mode_main_layout.addWidget(self.scenario_logo, alignment=Qt.AlignTop | Qt.AlignRight)
        
        layout.addWidget(mode_group)
        
        # ADB Configuration
        adb_group = QGroupBox("ADB Configuration")
        adb_layout = QGridLayout(adb_group)
        adb_layout.setSpacing(12)
        
        # Emulator Type
        adb_layout.addWidget(QLabel("Device/Emulator:"), 0, 0)
        self.emulator_combo = QComboBox()
        emulator_types = getattr(self.main_window, 'detected_emulator_types', [])
        self.emulator_combo.addItem("")
        self.emulator_combo.addItems(emulator_types)
        self.emulator_combo.addItem("Phone")
        self.emulator_combo.addItem("Other Emulator")
        self.emulator_combo.currentTextChanged.connect(self._on_emulator_change)
        adb_layout.addWidget(self.emulator_combo, 0, 1)
        
        # Device Address
        adb_layout.addWidget(QLabel("Device Address:"), 1, 0)
        self.device_addr = QLineEdit()
        self.device_addr.setPlaceholderText("127.0.0.1:7555 or auto")
        self.device_addr.textChanged.connect(
            lambda v: self._update_adb_config("device_address", v)
        )
        adb_layout.addWidget(self.device_addr, 1, 1)
        
        # ADB Path
        adb_layout.addWidget(QLabel("ADB Path:"), 2, 0)
        self.adb_path = QLineEdit()
        self.adb_path.setPlaceholderText("adb")
        self.adb_path.textChanged.connect(
            lambda v: self._update_adb_config("adb_path", v)
        )
        adb_layout.addWidget(self.adb_path, 2, 1)
        
        layout.addWidget(adb_group)

        # Other
        other_group = QGroupBox("API Mode (Experimental)")
        other_layout = QVBoxLayout(other_group)
        other_layout.setSpacing(12)

        self.api_enabled = QCheckBox("Turn on API Mode")
        self.api_enabled.stateChanged.connect(self._on_api_enabled_changed)
        other_layout.addWidget(self.api_enabled)

        self.api_settings_widget = QWidget()
        api_settings_layout = QVBoxLayout(self.api_settings_widget)
        api_settings_layout.setContentsMargins(0, 0, 0, 0)
        api_settings_layout.setSpacing(12)

        api_desc = QLabel(
            "Use Kise Uma Capture to read game status directly from network packets.\n"
            "This feature is experimental and depends on an external module.\n"
            "Check the Discord server for setup details and more information."
        )
        api_desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; margin-left: 25px;")
        api_settings_layout.addWidget(api_desc)

        api_url_row = QHBoxLayout()
        api_url_label = QLabel("API Address:")
        api_url_label.setFixedWidth(100)
        self.api_base_url = QLineEdit()
        self.api_base_url.setPlaceholderText("http://127.0.0.1:8123")
        self.api_base_url.editingFinished.connect(self._save_api_url)
        api_url_row.addWidget(api_url_label)
        api_url_row.addWidget(self.api_base_url)
        api_settings_layout.addLayout(api_url_row)

        api_timeout_row = QHBoxLayout()
        api_timeout_label = QLabel("Timeout (s):")
        api_timeout_label.setFixedWidth(100)
        self.api_timeout = QSpinBox()
        self.api_timeout.setMinimum(1)
        self.api_timeout.setMaximum(30)
        self.api_timeout.setValue(2)
        self.api_timeout.setFixedWidth(80)
        self.api_timeout.valueChanged.connect(self._save_api_timeout)
        api_timeout_row.addWidget(api_timeout_label)
        api_timeout_row.addWidget(self.api_timeout)
        api_timeout_row.addStretch()
        api_settings_layout.addLayout(api_timeout_row)

        api_btn_row = QHBoxLayout()
        self.test_api_btn = QPushButton("Test Connection")
        self.test_api_btn.setFixedWidth(140)
        self.test_api_btn.clicked.connect(self._test_api_connection)
        api_btn_row.addWidget(self.test_api_btn)
        api_btn_row.addStretch()
        api_settings_layout.addLayout(api_btn_row)

        other_layout.addWidget(self.api_settings_widget)

        layout.addWidget(other_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def load_config(self):
        """Load config values"""
        self._loading = True
        config = self.main_window.get_config()
        
        # Mode
        self.mode_combo.blockSignals(True)
        mode = config.get("mode", "ura")
        mode_display = {
            "ura": "URA Finale",
            "unity": "Unity Cup",
            "trackblazer": "Trackblazer",
        }.get(mode, "URA Finale")
        self.mode_combo.setCurrentText(mode_display)
        self.mode_combo.blockSignals(False)
        
        # Unity Team Name
        self.unity_team_combo.blockSignals(True)
        self.unity_team_combo.setCurrentText(config.get("unity_team_name", "Team Carrot"))
        self.unity_team_combo.blockSignals(False)
        
        # Set Unity Team visibility based on mode and update scenario logo
        is_unity = (mode == "unity")
        self.unity_team_row.setVisible(is_unity)
        self._update_scenario_logo(mode)
        
        # Emulator
        self.emulator_combo.blockSignals(True)
        self.emulator_combo.setCurrentText(config.get("emulator_type", ""))
        self.emulator_combo.blockSignals(False)
        
        # ADB
        self.device_addr.blockSignals(True)
        self.adb_path.blockSignals(True)
        adb = config.get("adb_config", {})
        self.device_addr.setText(adb.get("device_address", "127.0.0.1:7555"))
        self.adb_path.setText(adb.get("adb_path", "adb"))
        self.device_addr.blockSignals(False)
        self.adb_path.blockSignals(False)

        # API
        self.api_enabled.blockSignals(True)
        self.api_base_url.blockSignals(True)
        self.api_timeout.blockSignals(True)
        api = config.get("api", {})
        self.api_enabled.setChecked(api.get("enabled", False))
        self.api_base_url.setText(api.get("base_url", "http://127.0.0.1:8123"))
        self.api_timeout.setValue(api.get("timeout", 2))
        self.api_enabled.blockSignals(False)
        self.api_base_url.blockSignals(False)
        self.api_timeout.blockSignals(False)
        self._update_api_settings_visibility(api.get("enabled", False))
        
        self._loading = False
    
    def _on_mode_change(self, text):
        """Handle mode change"""
        if getattr(self, '_loading', False):
            return
        mode_map = {
            "URA Finale": "ura",
            "Unity Cup": "unity",
            "Trackblazer": "trackblazer",
        }
        mode = mode_map.get(text, "ura")
        self.main_window.update_config_value("mode", mode)
        self.main_window.save_config()
        
        # Toggle Unity Team visibility and update scenario logo
        is_unity = (mode == "unity")
        self.unity_team_row.setVisible(is_unity)
        self._update_scenario_logo(mode)
        
        # Update Unity fields visibility and reload training scores for new mode
        if hasattr(self.main_window, 'training_page'):
            self.main_window.training_page.update_unity_visibility()
            self.main_window.training_page._load_training_score_config()
        if hasattr(self.main_window, '_update_mode_dependent_navigation'):
            self.main_window._update_mode_dependent_navigation()
    
    def _on_unity_team_change(self, text):
        """Handle Unity Team change"""
        if getattr(self, '_loading', False):
            return
        self.main_window.update_config_value("unity_team_name", text)
        self.main_window.save_config()
    
    def _on_emulator_change(self, text):
        """Handle emulator type change"""
        if getattr(self, '_loading', False):
            return
        self.main_window.update_config_value("emulator_type", text)
        self.main_window.save_config()
        if text == "Phone":
            QMessageBox.information(
                self, "Phone Device",
                "When using Phone:\n• Auto address detection won't work\n• Manually enter ADB address\n• Resolution must be 1080x1920 (Portrait)"
            )
        elif text == "Other Emulator":
            QMessageBox.information(
                self, "Other Emulator",
                "When using Other Emulator:\n• Auto address detection won't work\n• Manually enter ADB address\n• Screenshot method will default to ADB"
            )
    
    def _update_adb_config(self, key, value):
        """Update ADB config"""
        if getattr(self, '_loading', False):
            return
        self.main_window.update_nested_config_value("adb_config", key, value)
        self.main_window.save_config()

    def _get_api_config(self):
        """Get current API config dict"""
        config = self.main_window.get_config()
        return config.get("api", {
            "enabled": False,
            "base_url": "http://127.0.0.1:8123",
            "timeout": 2
        })

    def _save_api_config(self, api_config):
        """Save API config"""
        if getattr(self, '_loading', False):
            return
        self.main_window.update_config_value("api", api_config)
        self.main_window.save_config()

    def _on_api_enabled_changed(self, state):
        """Handle API enabled checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self._update_api_settings_visibility(enabled)
        api_config = self._get_api_config()
        api_config["enabled"] = enabled
        self._save_api_config(api_config)

    def _update_api_settings_visibility(self, visible):
        """Show or hide API settings based on enabled state"""
        self.api_settings_widget.setVisible(visible)

    def _save_api_url(self):
        """Save API base URL"""
        api_config = self._get_api_config()
        base_url = self.api_base_url.text().strip() or "http://127.0.0.1:8123"
        if "://" not in base_url:
            base_url = f"http://{base_url}"
        api_config["base_url"] = base_url
        self._save_api_config(api_config)

    def _save_api_timeout(self, value):
        """Save API timeout"""
        api_config = self._get_api_config()
        api_config["timeout"] = value
        self._save_api_config(api_config)

    def _format_api_probe_result(self, endpoint, outcome):
        """Format a single endpoint probe result for display."""
        status = outcome.get("status", "unknown")
        elapsed_ms = outcome.get("elapsed_ms")
        elapsed_str = f" in {elapsed_ms} ms" if elapsed_ms is not None else ""
        if status == "ok":
            summary = outcome.get("summary")
            return f"{endpoint}: OK{elapsed_str}" + (f" ({summary})" if summary else "")
        if status == "waiting":
            return f"{endpoint}: waiting for game data{elapsed_str}"
        detail = outcome.get("detail", "unknown error")
        return f"{endpoint}: {status}{elapsed_str} ({detail})"

    def _build_api_fix_hints(self, url, results, timeout):
        """Build targeted troubleshooting hints from probe results."""
        hints = []

        if "localhost" in url:
            hints.append("If this fails only on some PCs, try http://127.0.0.1:8123 instead of http://localhost:8123.")

        failing = {ep: result for ep, result in results.items() if result.get("status") not in {"ok", "waiting"}}
        if not failing:
            return hints

        if any(result.get("status") == "timeout" for result in failing.values()):
            hints.append(f"Increase API timeout above {timeout}s and test again.")

        if any(result.get("status") == "connection_error" for result in failing.values()):
            hints.append("Confirm Kise Uma Capture is running on the same PC and listening on the configured address.")

        if any(result.get("status") == "invalid_json" for result in failing.values()):
            hints.append("The endpoint responded, but not with valid JSON. Check for a proxy, security software, or a non-KUC service on that port.")

        if any(result.get("status") == "invalid_url" for result in failing.values()):
            hints.append("The API address format is invalid. Use a full URL such as http://127.0.0.1:8123.")

        if any(result.get("status") == "schema_error" for result in failing.values()):
            hints.append("The API is reachable but the payload shape does not match what UMAT expects. Check KUC version compatibility.")

        if "/status" in failing and all(ep not in failing for ep in ["/training", "/skills", "/events"]):
            hints.append("UMAT depends on /status shape specifically. Compare the raw /status JSON on the affected PC against a working PC.")
        elif any(ep in failing for ep in ["/training", "/skills", "/events"]):
            hints.append("The bot uses /training, /skills, and /events too. A green /status test alone is not enough.")

        hints.append("If browser access works but this test fails, check Windows Firewall or antivirus rules for Python/UMAT, not just the browser.")
        return hints

    def _format_api_attempt_block(self, base_url, results):
        """Format all endpoint results for one base URL attempt."""
        lines = [f"Base URL: {base_url}"]
        endpoints = ["/status", "/training", "/skills", "/events"]
        lines.extend(self._format_api_probe_result(endpoint, results[endpoint]) for endpoint in endpoints)
        return lines

    def _get_api_test_urls(self, raw_url):
        """Return primary and alternate loopback URLs for testing."""
        base_url = (raw_url or "http://127.0.0.1:8123").strip().rstrip("/")
        if "://" not in base_url:
            base_url = f"http://{base_url}"
        urls = [base_url]

        try:
            parsed = urlparse(base_url)
            host = parsed.hostname
            if host in {"localhost", "127.0.0.1"}:
                alt_host = "127.0.0.1" if host == "localhost" else "localhost"
                netloc = alt_host
                if parsed.port:
                    netloc = f"{alt_host}:{parsed.port}"
                if parsed.username:
                    auth = parsed.username
                    if parsed.password:
                        auth += f":{parsed.password}"
                    netloc = f"{auth}@{netloc}"
                alt_url = urlunparse((
                    parsed.scheme or "http",
                    netloc,
                    parsed.path or "",
                    parsed.params or "",
                    parsed.query or "",
                    parsed.fragment or "",
                )).rstrip("/")
                if alt_url not in urls:
                    urls.append(alt_url)
        except Exception:
            pass

        return urls

    def _probe_api_endpoint(self, session, base_url, endpoint, timeout):
        """Probe one API endpoint and validate the payload shape UMAT relies on."""
        import requests
        import time

        url = f"{base_url}{endpoint}"
        started = time.perf_counter()

        def _result(status, detail=None, summary=None):
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            payload = {"status": status, "elapsed_ms": elapsed_ms, "url": url}
            if detail is not None:
                payload["detail"] = detail
            if summary is not None:
                payload["summary"] = summary
            return payload

        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.InvalidSchema as e:
            return _result("invalid_url", repr(e))
        except requests.MissingSchema as e:
            return _result("invalid_url", repr(e))
        except requests.Timeout:
            return _result("timeout", f"timed out after {timeout}s")
        except requests.ConnectionError as e:
            return _result("connection_error", repr(e))
        except requests.HTTPError as e:
            code = getattr(e.response, "status_code", "HTTP error")
            body = ""
            try:
                body = (e.response.text or "")[:200].strip()
            except Exception:
                pass
            detail = f"HTTP {code}"
            if body:
                detail += f", body={body}"
            return _result("http_error", detail)
        except ValueError as e:
            return _result("invalid_json", repr(e))
        except requests.RequestException as e:
            return _result("request_error", repr(e))

        if isinstance(data, dict) and data.get("status") == "waiting":
            return _result("waiting")

        if endpoint == "/status":
            required_keys = ["year", "stats", "energy", "mood", "current_skill_points"]
            missing = [key for key in required_keys if key not in data]
            if missing:
                return _result("schema_error", f"missing keys: {', '.join(missing)}")
            if not isinstance(data.get("stats"), dict):
                return _result("schema_error", "stats is not an object")
            if not isinstance(data.get("energy"), dict):
                return _result("schema_error", "energy is not an object")
            if not isinstance(data.get("mood"), dict):
                return _result("schema_error", "mood is not an object")
            stats = data.get("stats", {})
            summary = (
                f"{data.get('year', 'N/A')}, "
                f"mood={data.get('mood', {}).get('name', 'N/A')}, "
                f"SPD={stats.get('spd', 'N/A')}, "
                f"STA={stats.get('sta', 'N/A')}, "
                f"PWR={stats.get('pwr', 'N/A')}, "
                f"GUTS={stats.get('guts', 'N/A')}, "
                f"WIT={stats.get('wit', 'N/A')}"
            )
            return _result("ok", summary=summary)

        if endpoint == "/training":
            trainings = data.get("trainings")
            if not isinstance(trainings, list):
                return _result("schema_error", "trainings is not a list")
            return _result("ok", summary=f"{len(trainings)} trainings")

        if endpoint == "/skills":
            skills = data.get("skills")
            if not isinstance(skills, list):
                return _result("schema_error", "skills is not a list")
            points = data.get("current_skill_points", "N/A")
            return _result("ok", summary=f"{len(skills)} skills, {points} pts")

        if endpoint == "/events":
            events = data.get("events")
            if not isinstance(events, list):
                return _result("schema_error", "events is not a list")
            return _result("ok", summary=f"{len(events)} events")

        return _result("ok")

    def _test_api_connection(self):
        """Probe all API endpoints UMAT depends on and report actionable diagnostics."""
        import requests

        raw_url = self.api_base_url.text().strip() or "http://127.0.0.1:8123"
        configured_timeout = self.api_timeout.value()
        test_timeout = 10
        endpoints = ["/status", "/training", "/skills", "/events"]
        candidate_urls = self._get_api_test_urls(raw_url)
        attempts = []

        try:
            session = requests.Session()
            for base_url in candidate_urls:
                results = {
                    endpoint: self._probe_api_endpoint(session, base_url, endpoint, test_timeout)
                    for endpoint in endpoints
                }
                attempts.append((base_url, results))
        except Exception as e:
            QMessageBox.critical(self, "API Test", f"Unexpected test failure:\n{str(e)}")
            return

        primary_url, primary_results = attempts[0]
        alt_attempt = attempts[1] if len(attempts) > 1 else None
        primary_waiting = [ep for ep, result in primary_results.items() if result.get("status") == "waiting"]
        primary_failures = [ep for ep, result in primary_results.items() if result.get("status") not in {"ok", "waiting"}]
        lines = [
            f"Configured URL: {raw_url.rstrip('/')}",
            f"Configured timeout: {configured_timeout}s",
            f"Test timeout: {test_timeout}s",
            "",
        ]
        lines.extend(self._format_api_attempt_block(primary_url, primary_results))

        used_alt_success = False
        alt_url = None
        alt_results = None
        alt_waiting = []
        alt_failures = []
        if alt_attempt:
            alt_url, alt_results = alt_attempt
            alt_waiting = [ep for ep, result in alt_results.items() if result.get("status") == "waiting"]
            alt_failures = [ep for ep, result in alt_results.items() if result.get("status") not in {"ok", "waiting"}]
            primary_all_bad = all(result.get("status") not in {"ok", "waiting"} for result in primary_results.values())
            alt_has_signal = any(result.get("status") in {"ok", "waiting"} for result in alt_results.values())
            if primary_failures and primary_all_bad and alt_has_signal:
                used_alt_success = True
                lines.append("")
                lines.append("Alternate loopback address test:")
                lines.extend(self._format_api_attempt_block(alt_url, alt_results))

        if used_alt_success:
            lines.append("")
            lines.append("Conclusion:")
            lines.append(f"- The configured URL failed, but {alt_url} responded.")
            lines.append(f"- Change API Address to {alt_url}.")
            QMessageBox.warning(self, "API Test", "\n".join(lines))
            return

        hints = self._build_api_fix_hints(primary_url, primary_results, test_timeout)

        if primary_waiting and not primary_failures:
            lines.append("")
            lines.append("Conclusion:")
            lines.append("- Server is reachable, but some endpoints are waiting for live game data.")
            lines.append("- Open an active career run and test again if UMAT still cannot use API mode.")
            if hints:
                lines.append("")
                lines.append("Suggested fixes:")
                lines.extend(f"- {hint}" for hint in hints)
            QMessageBox.information(self, "API Test", "\n".join(lines))
            return

        if primary_failures:
            lines.append("")
            lines.append("Conclusion:")
            lines.append("- One or more required endpoints failed.")
            lines.append("- Review the endpoint lines above for the exact error and timing.")
            if alt_attempt and not used_alt_success:
                lines.append("")
                lines.append("Alternate loopback address test:")
                lines.extend(self._format_api_attempt_block(alt_url, alt_results))
                if alt_failures or alt_waiting:
                    lines.append("- Alternate address did not fully resolve the issue.")
            if hints:
                lines.append("")
                lines.append("Suggested fixes:")
                lines.extend(f"- {hint}" for hint in hints)
            QMessageBox.warning(self, "API Test", "\n".join(lines))
            return

        lines.append("")
        lines.append("Conclusion:")
        lines.append("- All required endpoints returned valid JSON in the shape UMAT expects.")
        QMessageBox.information(self, "API Test", "\n".join(lines))
    
    def _update_scenario_logo(self, mode):
        """Update the scenario logo based on the selected mode"""
        # Get assets directory path
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "scenario")
        
        if mode == "unity":
            logo_path = os.path.join(assets_dir, "Unity_Cup.png")
        elif mode == "trackblazer":
            logo_path = os.path.join(assets_dir, "Trackblazer.png")
        else:
            logo_path = os.path.join(assets_dir, "Ura_Finale.png")
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale to 200px height while keeping aspect ratio
            scaled_pixmap = pixmap.scaledToHeight(200, Qt.SmoothTransformation)
            self.scenario_logo.setPixmap(scaled_pixmap)
        else:
            self.scenario_logo.clear()
