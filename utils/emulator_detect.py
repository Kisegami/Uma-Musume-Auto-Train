"""
Lightweight emulator discovery and ADB connect helpers (no external deps).
Adapted from standalone_emulator_autodetect for GUI/runtime use.
"""

from __future__ import annotations

import codecs
import os
import re
import subprocess
import typing as t
import winreg

try:
    import psutil  # type: ignore
except ModuleNotFoundError:
    psutil = None

try:
    from utils.device import _get_adb_path
except ImportError:
    # Fallback if utils.device is not available
    def _get_adb_path():
        return "adb"


def abspath(path: str) -> str:
    return os.path.abspath(path).replace("\\", "/")


def iter_folder(folder: str, *, is_dir: bool = False, ext: str | None = None) -> t.Iterable[str]:
    if not os.path.exists(folder):
        return
    for entry in os.scandir(folder):
        if is_dir and not entry.is_dir():
            continue
        if ext and not entry.name.lower().endswith(ext.lower()):
            continue
        yield entry.path.replace("\\", "/")


def remove_duplicated_path(paths: t.Iterable[str]) -> list[str]:
    dedup = {}
    for p in paths:
        dedup.setdefault(p.lower(), p)
    return list(dedup.values())


def get_serial_pair(serial: str) -> tuple[str | None, str | None]:
    if serial.startswith("127.0.0.1:"):
        try:
            port = int(serial[10:])
            if 5555 <= port <= 5555 + 32:
                return f"127.0.0.1:{port}", f"emulator-{port - 1}"
        except (ValueError, IndexError):
            pass
    if serial.startswith("emulator-"):
        try:
            port = int(serial[9:])
            if 5554 <= port <= 5554 + 32:
                return f"127.0.0.1:{port + 1}", f"emulator-{port}"
        except (ValueError, IndexError):
            pass
    return None, None


class Emulator:
    LDPlayer9 = "LDPlayer9"
    MuMuPlayer12 = "MuMuPlayer12"
    MuMuPlayer = "MuMuPlayer"
    MuMuPlayerX = "MuMuPlayerX"
    BlueStacks4 = "BlueStacks4"
    BlueStacks5 = "BlueStacks5"
    NoxPlayer = "NoxPlayer"
    NoxPlayer64 = "NoxPlayer64"
    MEmuPlayer = "MEmuPlayer"
    LDPlayer3 = "LDPlayer3"
    LDPlayer4 = "LDPlayer4"

    def __init__(self, path: str):
        self.path = path.replace("\\", "/")
        self.dir = os.path.dirname(self.path)
        self.type = self.path_to_type(self.path)

    def __bool__(self):
        return bool(self.type)

    @staticmethod
    def path_to_type(path: str) -> str:
        folder, exe = os.path.split(path)
        folder, dir1 = os.path.split(folder)
        folder, dir2 = os.path.split(folder)
        exe = exe.lower()
        dir1 = dir1.lower()
        dir2 = dir2.lower()
        if exe == "dnplayer.exe":
            if dir1 == "ldplayer9":
                return Emulator.LDPlayer9
            if dir1 == "ldplayer4":
                return Emulator.LDPlayer4
            if dir1 == "ldplayer":
                return Emulator.LDPlayer3
        if exe in ["mumuplayer.exe", "mumunxmain.exe"]:
            return Emulator.MuMuPlayer12
        if exe == "nemuplayer.exe":
            if dir2 == "nemu9":
                return Emulator.MuMuPlayerX
            return Emulator.MuMuPlayer
        if exe == "memu.exe":
            return Emulator.MEmuPlayer
        if exe == "nox.exe":
            return Emulator.NoxPlayer if dir2 == "nox" else Emulator.NoxPlayer64
        if exe in ["bluestacks.exe", "bluestacksgp.exe", "hd-player.exe"]:
            if dir1 in ["bluestacks_nxt", "bluestacks_nxt_cn"]:
                return Emulator.BlueStacks5
            return Emulator.BlueStacks4
        return ""

    @staticmethod
    def multi_to_single(exe: str) -> t.Iterable[str]:
        if "MuMuManager.exe" in exe:
            yield exe.replace("MuMuManager.exe", "MuMuPlayer.exe")
        elif "MuMuMultiPlayer.exe" in exe:
            yield exe.replace("MuMuMultiPlayer.exe", "MuMuPlayer.exe")
        elif "NemuMultiPlayer.exe" in exe:
            yield exe.replace("NemuMultiPlayer.exe", "NemuPlayer.exe")
        elif "dnmultiplayer.exe" in exe:
            yield exe.replace("dnmultiplayer.exe", "dnplayer.exe")
        else:
            yield exe

    @staticmethod
    def vbox_file_to_serial(file: str) -> str:
        regex = re.compile(r'<*?hostport="(.*?)".*?guestport="5555"/>')
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    res = regex.search(line)
                    if res:
                        return f"127.0.0.1:{res.group(1)}"
            return ""
        except FileNotFoundError:
            return ""

    def iter_instances(self) -> t.Iterable["EmulatorInstance"]:
        if self.type in [Emulator.LDPlayer3, Emulator.LDPlayer4, Emulator.LDPlayer9]:
            regex = re.compile(r"^leidian(\d+)$")
            for folder in self.list_folder("./vms", is_dir=True):
                name = os.path.basename(folder)
                res = regex.match(name)
                if not res:
                    continue
                port = int(res.group(1)) * 2 + 5555
                yield EmulatorInstance(serial=f"127.0.0.1:{port}", name=name, path=self.path)
        elif self.type == Emulator.MuMuPlayer:
            yield EmulatorInstance(serial="127.0.0.1:7555", name="", path=self.path)
        elif self.type in [Emulator.MuMuPlayerX, Emulator.MuMuPlayer12]:
            for folder in self.list_folder("../vms", is_dir=True):
                for file in iter_folder(folder, ext=".nemu"):
                    serial = self.vbox_file_to_serial(file)
                    name = os.path.basename(folder)
                    if serial:
                        yield EmulatorInstance(serial=serial, name=name, path=self.path)
                    else:
                        inst = EmulatorInstance(serial="", name=name, path=self.path)
                        if inst.mumu12_id is not None:
                            inst.serial = f"127.0.0.1:{16384 + 32 * inst.mumu12_id}"
                            yield inst
        elif self.type == Emulator.MEmuPlayer:
            for folder in self.list_folder("./MemuHyperv VMs", is_dir=True):
                for file in iter_folder(folder, ext=".memu"):
                    serial = self.vbox_file_to_serial(file)
                    if serial:
                        yield EmulatorInstance(serial=serial, name=os.path.basename(folder), path=self.path)

    def list_folder(self, folder: str, *, is_dir: bool = False, ext: str | None = None) -> list[str]:
        return list(iter_folder(self.abspath(folder), is_dir=is_dir, ext=ext))

    def abspath(self, path: str, folder: str | None = None) -> str:
        if folder is None:
            folder = self.dir
        return abspath(os.path.join(folder, path))


class EmulatorInstance:
    def __init__(self, serial: str, name: str, path: str):
        self.serial = serial
        self.name = name
        self.path = path

    @property
    def emulator(self) -> Emulator:
        return Emulator(self.path)

    @property
    def type(self) -> str:
        return self.emulator.type

    @property
    def mumu12_id(self) -> int | None:
        res = re.search(r"MuMuPlayer(?:Global)?-12.0-(\d+)", self.name)
        if res:
            return int(res.group(1))
        res = re.search(r"YXArkNights-12.0-(\d+)", self.name)
        if res:
            return int(res.group(1))
        return None

    @property
    def ldplayer_id(self) -> int | None:
        res = re.search(r"leidian(\d+)", self.name)
        if res:
            return int(res.group(1))
        return None


class EmulatorManager:
    def __init__(self):
        self._all_emulators: list[Emulator] | None = None
        self._all_instances: list[EmulatorInstance] | None = None

    @property
    def all_emulators(self) -> list[Emulator]:
        if self._all_emulators is not None:
            return self._all_emulators
        exe_set: set[str] = set()
        for file in self._iter_mui_cache():
            if Emulator.path_to_type(file) and os.path.exists(file):
                exe_set.add(file)
        for file in self._iter_user_assist():
            if Emulator.path_to_type(file) and os.path.exists(file):
                exe_set.add(file)
        for file in self._iter_ldplayer_install_path():
            exe_set.add(file)
        for uninstall in self._iter_uninstall_registry():
            base_dir = abspath(os.path.dirname(uninstall))
            for file in iter_folder(base_dir, ext=".exe"):
                if Emulator.path_to_type(file) and os.path.exists(file):
                    exe_set.add(file)
        for file in self._iter_running_emulator():
            if os.path.exists(file):
                exe_set.add(file)
        exe_list = [Emulator(path).path for path in exe_set if Emulator.path_to_type(path)]
        self._all_emulators = [Emulator(path) for path in remove_duplicated_path(exe_list)]
        return self._all_emulators

    @property
    def all_instances(self) -> list[EmulatorInstance]:
        if self._all_instances is not None:
            return self._all_instances
        inst: list[EmulatorInstance] = []
        for emulator in self.all_emulators:
            inst.extend(list(emulator.iter_instances()))
        self._all_instances = sorted(inst, key=lambda x: str(x))
        return self._all_instances

    def instances_by_type(self, emulator_type: str) -> list[EmulatorInstance]:
        return [i for i in self.all_instances if i.type == emulator_type]

    @staticmethod
    def adb_devices(adb_path: str | None = None) -> list[tuple[str, str]]:
        # Use the smart ADB path resolver if no path provided or if it's just "adb"
        if adb_path is None or adb_path == "adb":
            try:
                adb_path = _get_adb_path()
            except Exception:
                adb_path = "adb"
        
        try:
            proc = subprocess.run([adb_path, "devices"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"ADB executable not found at '{adb_path}'. "
                "Please ensure ADB is installed and accessible. "
                "You can either:\n"
                "1. Install Android SDK Platform Tools and add ADB to your PATH\n"
                "2. Set the full path to adb.exe in config.json (adb_config.adb_path)\n"
                "3. Install adbutils package which includes bundled ADB"
            )
        stdout = proc.stdout.decode(errors="ignore").replace("\r\r\n", "\n").replace("\r\n", "\n")
        devices: list[tuple[str, str]] = []
        for line in stdout.splitlines():
            if line.startswith("List") or "\t" not in line:
                continue
            serial, status = line.split("\t")
            devices.append((serial, status))
        return devices

    def connect_serials(self, serials: list[str], adb_path: str | None = None) -> list[tuple[str, str]]:
        # Use the smart ADB path resolver if no path provided or if it's just "adb"
        if adb_path is None or adb_path == "adb":
            try:
                adb_path = _get_adb_path()
            except Exception:
                adb_path = "adb"
        
        results: list[tuple[str, str]] = []
        try:
            for serial, status in self.adb_devices(adb_path):
                if status == "offline":
                    subprocess.run([adb_path, "disconnect", serial], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except FileNotFoundError as e:
            # Re-raise with better context
            raise
        for serial in serials:
            try:
                proc = subprocess.run([adb_path, "connect", serial], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                results.append((serial, proc.stdout.decode(errors="ignore").strip()))
            except FileNotFoundError:
                # Re-raise with better context
                raise FileNotFoundError(
                    f"ADB executable not found at '{adb_path}'. "
                    "Please ensure ADB is installed and accessible. "
                    "You can either:\n"
                    "1. Install Android SDK Platform Tools and add ADB to your PATH\n"
                    "2. Set the full path to adb.exe in config.json (adb_config.adb_path)\n"
                    "3. Install adbutils package which includes bundled ADB"
                )
        return results

    def choose_running_instance(self, emulator_type: str, adb_path: str | None = None) -> tuple[EmulatorInstance | None, str | None, list[str]]:
        instances = self.instances_by_type(emulator_type)
        if not instances:
            return None, None, []
        serials: list[str] = []
        for inst in instances:
            if inst.serial:
                serials.append(inst.serial)
            port_serial, emu_serial = get_serial_pair(inst.serial)
            if emu_serial:
                serials.append(emu_serial)
        serials = remove_duplicated_path(serials)
        self.connect_serials(serials, adb_path=adb_path)
        devices = self.adb_devices(adb_path=adb_path)
        running = [s for s, status in devices if status == "device" and s in serials]
        
        if not running:
            return None, None, running
        
        # Normalize serials to group pairs (same emulator instance with different formats)
        # Prefer 127.0.0.1:X format as the primary form
        def normalize_serial(serial: str) -> str:
            """Normalize serial to primary form (127.0.0.1:X preferred)"""
            if serial.startswith("127.0.0.1:"):
                return serial
            if serial.startswith("emulator-"):
                port_serial, _ = get_serial_pair(serial)
                if port_serial:
                    return port_serial
            return serial
        
        # Group running serials by their normalized form (same emulator instance)
        normalized_to_serials: dict[str, list[str]] = {}
        for serial in running:
            normalized = normalize_serial(serial)
            if normalized not in normalized_to_serials:
                normalized_to_serials[normalized] = []
            normalized_to_serials[normalized].append(serial)
        
        # Count distinct emulator instances (after normalization)
        distinct_count = len(normalized_to_serials)
        
        if distinct_count == 1:
            # Single emulator instance (may have multiple serial formats like 127.0.0.1:5557 and emulator-5556)
            primary_serial = list(normalized_to_serials.keys())[0]
            # Find matching instance - check if instance serial matches the normalized serial
            inst = next(
                (i for i in instances 
                 if i.serial == primary_serial 
                 or normalize_serial(i.serial) == primary_serial
                 or get_serial_pair(i.serial)[0] == primary_serial
                 or get_serial_pair(i.serial)[1] == primary_serial),
                instances[0] if instances else None
            )
            if inst:
                return inst, primary_serial, running
        
        # Multiple distinct emulator instances
        if distinct_count >= 2:
            return None, None, running
        
        return None, None, running

    # --- discovery helpers
    @staticmethod
    def _iter_user_assist() -> t.Iterable[str]:
        path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"
        regex_hash = re.compile(r"{.*}")
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as reg:
                folders = _list_key(reg)
        except FileNotFoundError:
            return
        for folder in folders:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{path}\\{folder}\\Count") as reg:
                    for key in _list_reg(reg):
                        key_name = codecs.decode(key[0], "rot-13")
                        if regex_hash.search(key_name):
                            continue
                        for file in Emulator.multi_to_single(key_name):
                            yield file
            except FileNotFoundError:
                continue

    @staticmethod
    def _iter_mui_cache() -> t.Iterable[str]:
        path = r"Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as reg:
                rows = _list_reg(reg)
        except FileNotFoundError:
            return
        regex = re.compile(r"(^.*\.exe)\.")
        for row in rows:
            res = regex.search(row[0])
            if not res:
                continue
            for file in Emulator.multi_to_single(res.group(1)):
                yield file

    @staticmethod
    def _iter_ldplayer_install_path() -> t.Iterable[str]:
        for path in [r"SOFTWARE\leidian\ldplayer", r"SOFTWARE\leidian\ldplayer9"]:
            folder = _get_install_dir_from_reg(path, "InstallDir")
            if folder:
                exe = abspath(os.path.join(folder, "./dnplayer.exe"))
                if Emulator.path_to_type(exe) and os.path.exists(exe):
                    yield exe

    @staticmethod
    def _iter_uninstall_registry() -> t.Iterable[str]:
        uninstall_roots = [
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        names = [
            "Nox",
            "Nox64",
            "BlueStacks",
            "BlueStacks_nxt",
            "BlueStacks_cn",
            "BlueStacks_nxt_cn",
            "LDPlayer",
            "LDPlayer4",
            "LDPlayer9",
            "leidian",
            "leidian4",
            "leidian9",
            "Nemu",
            "Nemu9",
            "MuMuPlayer",
            "MuMuPlayer-12.0",
            "MuMu Player 12.0",
            "MEmu",
        ]
        for root in uninstall_roots:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root) as reg:
                    software_list = _list_key(reg)
            except FileNotFoundError:
                continue
            for software in software_list:
                if software not in names:
                    continue
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{root}\\{software}") as sreg:
                        uninstall = winreg.QueryValueEx(sreg, "UninstallString")[0]
                except FileNotFoundError:
                    continue
                if not uninstall:
                    continue
                res = re.search('"(.+?)"', uninstall)
                uninstall_path = res.group(1) if res else uninstall
                yield uninstall_path

    @staticmethod
    def _iter_running_emulator() -> t.Iterable[str]:
        if psutil is None:
            return
        for pid in psutil.pids():
            proc = psutil._psplatform.Process(pid)  # type: ignore[attr-defined]
            try:
                exe = proc.cmdline()[0].replace("\\\\", "/").replace("\\", "/")
            except Exception:
                continue
            if Emulator.path_to_type(exe):
                yield exe


def _list_reg(reg) -> list[tuple]:
    rows = []
    idx = 0
    try:
        while True:
            rows.append(winreg.EnumValue(reg, idx))
            idx += 1
    except OSError:
        pass
    return rows


def _list_key(reg) -> list[str]:
    rows = []
    idx = 0
    try:
        while True:
            rows.append(winreg.EnumKey(reg, idx))
            idx += 1
    except OSError:
        pass
    return rows


def _get_install_dir_from_reg(path: str, key: str) -> str | None:
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, path) as reg:
                return winreg.QueryValueEx(reg, key)[0]
        except FileNotFoundError:
            continue
    return None


def list_emulator_types() -> list[str]:
    mgr = EmulatorManager()
    types = {inst.type for inst in mgr.all_instances}
    return sorted(types)


def resolve_emulator_connection(emulator_type: str, adb_path: str | None = None):
    """
    Returns tuple (instance, serial, running_list).
    instance/serial None means ambiguous or not found.
    """
    mgr = EmulatorManager()
    return mgr.choose_running_instance(emulator_type, adb_path=adb_path)

