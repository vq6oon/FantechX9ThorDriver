"""
Software "Fire Key" untuk Fantech X9 Thor (Linux).

Cara kerja:
  - Mouse di-grab lewat evdev (event dari mouse tidak sampai ke desktop langsung)
  - Semua event diteruskan ulang lewat virtual device (uinput)
  - Tombol "trigger" dicegat dan diganti dengan perilaku Fire Key:
        Double Click          -> sekali tekan = 2 klik cepat
        Auto Clicker (Hold)   -> ditahan = klik terus-menerus
        Auto Clicker (Toggle) -> tekan sekali = mulai, tekan lagi = berhenti

Dependensi: pip install evdev   (butuh akses ke /dev/input/event* dan /dev/uinput)

Fire Key berjalan sebagai proses background (daemon) yang terpisah dari GUI,
jadi tetap aktif walau GUI ditutup:
    python3 fire_key.py --daemon    # jalankan daemon (biasanya dijalankan GUI / systemd)
    python3 fire_key.py --stop      # hentikan daemon
Pengaturan dibaca live dari ~/.config/fantech-x9/fire_key.conf
"""
import configparser
import os
import select
import signal
import subprocess
import sys
import threading
import time

try:
    import evdev
    from evdev import ecodes, InputDevice, UInput
except ImportError:  # dicek saat start()
    evdev = None

VENDOR_ID = 0x18f8
PRODUCT_ID = 0x0fc0

MODES = ["Double Click", "Auto Clicker (Hold)", "Auto Clicker (Toggle)"]
BUTTONS = ["left", "middle", "right", "forward", "backward"]


def _button_codes():
    return {
        "left": ecodes.BTN_LEFT,
        "middle": ecodes.BTN_MIDDLE,
        "right": ecodes.BTN_RIGHT,
        "forward": ecodes.BTN_EXTRA,
        "backward": ecodes.BTN_SIDE,
    }


class FireKeyEngine(object):
    def __init__(self, vendor_id=VENDOR_ID, product_id=PRODUCT_ID):
        self.vendor_id = vendor_id
        self.product_id = product_id

        # Setting ini dibaca live, jadi bisa diubah saat engine jalan
        self.mode = MODES[0]
        self.trigger = "forward"
        self.target = "left"
        self.cps = 10               # klik per detik (auto clicker)
        self.double_delay_ms = 20   # jarak antar 2 klik (double click)

        self.last_error = None

        self._dev = None
        self._ui = None
        self._thread = None
        self._worker = None
        self._codes = {}
        self._stop = threading.Event()
        self._clicking = threading.Event()
        self._write_lock = threading.Lock()
        self._seq_lock = threading.Lock()

    # ------------------------------------------------------------------ API
    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def configure(self, **settings):
        for key, value in settings.items():
            if hasattr(self, key) and not key.startswith("_"):
                setattr(self, key, value)

    def start(self):
        if evdev is None:
            raise RuntimeError("Modul python-evdev belum terinstall.\nJalankan: pip install evdev")
        if self.running:
            return

        self._codes = _button_codes()
        dev = self._find_device()
        try:
            ui = UInput.from_device(dev, name="Fantech X9 Thor (Fire Key)")
        except PermissionError:
            dev.close()
            raise PermissionError("Tidak punya akses ke /dev/uinput. Lihat 99-fantech-x9.rules "
                                  "atau jalankan sebagai root.")
        try:
            dev.grab()
        except OSError as exc:
            ui.close()
            dev.close()
            raise RuntimeError("Gagal meng-grab mouse (mungkin sedang dipakai program lain): %s" % exc)

        self._dev, self._ui = dev, ui
        self.last_error = None
        self._stop.clear()
        self._clicking.clear()
        self._worker = threading.Thread(target=self._auto_click_loop, daemon=True)
        self._worker.start()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._clicking.clear()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._thread = None
        # Jaga-jaga kalau thread belum sempat beres-beres: lepas grab paksa
        self._clicking.clear()
        self._cleanup()

    # ------------------------------------------------------------- internals
    def _find_device(self):
        permission_denied = False
        for path in evdev.list_devices():
            try:
                dev = InputDevice(path)
            except PermissionError:
                permission_denied = True
                continue
            except OSError:
                continue
            if dev.info.vendor == self.vendor_id and dev.info.product == self.product_id:
                if ecodes.BTN_LEFT in dev.capabilities().get(ecodes.EV_KEY, []):
                    return dev
            dev.close()
        if permission_denied:
            raise PermissionError("Tidak punya akses ke /dev/input/event*. Lihat 99-fantech-x9.rules "
                                  "atau jalankan sebagai root.")
        raise RuntimeError("Mouse Fantech X9 tidak ditemukan sebagai input device.")

    def _run(self):
        dev = self._dev
        try:
            while not self._stop.is_set():
                ready, _, _ = select.select([dev.fd], [], [], 0.1)
                if not ready:
                    continue
                try:
                    events = list(dev.read())
                except BlockingIOError:
                    continue
                for ev in events:
                    self._handle(ev)
        except OSError as exc:  # mouse dicabut
            self.last_error = str(exc)
        finally:
            self._stop.set()
            self._clicking.clear()
            if self._worker is not None:
                self._worker.join(timeout=1)
            self._cleanup()

    def _cleanup(self):
        with self._write_lock:
            dev, ui = self._dev, self._ui
            self._dev = self._ui = None
        if dev is not None:
            try:
                dev.ungrab()
            except OSError:
                pass
            dev.close()
        if ui is not None:
            ui.close()

    def _handle(self, ev):
        if ev.type == ecodes.EV_KEY and ev.code == self._codes[self.trigger]:
            if ev.value == 1:
                self._on_press()
            elif ev.value == 0:
                self._on_release()
            return  # event asli tombol trigger tidak diteruskan
        self._emit([(ev.type, ev.code, ev.value)])

    def _on_press(self):
        if self.mode == "Double Click":
            threading.Thread(target=self._double_click, daemon=True).start()
        elif self.mode == "Auto Clicker (Hold)":
            self._clicking.set()
        elif self.mode == "Auto Clicker (Toggle)":
            if self._clicking.is_set():
                self._clicking.clear()
            else:
                self._clicking.set()

    def _on_release(self):
        if self.mode == "Auto Clicker (Hold)":
            self._clicking.clear()

    def _emit(self, events):
        with self._write_lock:
            ui = self._ui
            if ui is None:
                return
            for etype, code, value in events:
                ui.write(etype, code, value)
            if not (events[-1][0] == ecodes.EV_SYN):
                ui.syn()

    def _click(self, hold):
        code = self._codes[self.target]
        self._emit([(ecodes.EV_KEY, code, 1)])
        time.sleep(hold)
        self._emit([(ecodes.EV_KEY, code, 0)])

    def _double_click(self):
        with self._seq_lock:
            half = max(self.double_delay_ms, 2) / 1000.0 / 2
            self._click(half)
            time.sleep(half)
            self._click(half)

    def _auto_click_loop(self):
        while not self._stop.is_set():
            if not self._clicking.wait(0.1):
                continue
            period = 1.0 / max(1.0, float(self.cps))
            hold = min(0.01, period / 2)
            with self._seq_lock:
                self._click(hold)
            time.sleep(period - hold)


# =============================================================================
# Pengaturan bersama (GUI menulis, daemon membaca) + kontrol daemon
# =============================================================================
CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "fantech-x9")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "fire_key.conf")
STATUS_FILE = os.path.join(CONFIG_DIR, "fire_key.status")
PID_FILE = os.path.join(CONFIG_DIR, "fire_key.pid")
LOG_FILE = os.path.join(CONFIG_DIR, "fire_key.log")

DEFAULT_SETTINGS = {
    "enabled": False,
    "mode": MODES[0],
    "trigger": "forward",
    "target": "left",
    "cps": 10,
    "double_delay_ms": 20,
}


def load_settings():
    settings = dict(DEFAULT_SETTINGS)
    config = configparser.ConfigParser()
    try:
        config.read(SETTINGS_FILE)
    except configparser.Error:
        return settings
    if not config.has_section("Fire_Key"):
        return settings
    section = config["Fire_Key"]
    try:
        settings["enabled"] = section.getboolean("enabled", settings["enabled"])
        settings["cps"] = max(1, min(50, section.getint("cps", settings["cps"])))
        settings["double_delay_ms"] = max(5, min(100, section.getint("double_delay_ms",
                                                                      settings["double_delay_ms"])))
    except ValueError:
        pass
    if section.get("mode") in MODES:
        settings["mode"] = section.get("mode")
    if section.get("trigger") in BUTTONS:
        settings["trigger"] = section.get("trigger")
    if section.get("target") in BUTTONS:
        settings["target"] = section.get("target")
    return settings


def save_settings(settings):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = configparser.ConfigParser()
    config["Fire_Key"] = {key: str(int(value)) if isinstance(value, bool) else str(value)
                          for key, value in settings.items()}
    tmp = SETTINGS_FILE + ".tmp"
    with open(tmp, "w") as handle:
        config.write(handle)
    os.replace(tmp, SETTINGS_FILE)


def write_status(text):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(STATUS_FILE, "w") as handle:
        handle.write(text)


def read_status():
    try:
        with open(STATUS_FILE) as handle:
            return handle.read().strip()
    except OSError:
        return ""


def clear_status():
    try:
        os.remove(STATUS_FILE)
    except OSError:
        pass


def daemon_pid():
    """PID daemon yang sedang jalan, atau None."""
    try:
        with open(PID_FILE) as handle:
            pid = int(handle.read().strip())
        os.kill(pid, 0)
        with open("/proc/%d/cmdline" % pid, "rb") as handle:
            cmdline = handle.read()
    except (OSError, ValueError):
        return None
    return pid if b"fire_key" in cmdline else None


def start_daemon():
    """Jalankan daemon terpisah dari proses ini (tetap hidup walau GUI ditutup)."""
    if daemon_pid() is not None:
        return
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(LOG_FILE, "ab") as log:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "--daemon"],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                         start_new_session=True, close_fds=True)


def stop_daemon(timeout=3.0):
    pid = daemon_pid()
    if pid is None:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    deadline = time.time() + timeout
    while time.time() < deadline and daemon_pid() is not None:
        time.sleep(0.05)


def run_daemon():
    if daemon_pid() is not None:
        print("Fire Key daemon sudah berjalan.")
        return 1
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(PID_FILE, "w") as handle:
        handle.write(str(os.getpid()))

    quit_event = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: quit_event.set())
    signal.signal(signal.SIGINT, lambda *_: quit_event.set())
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    engine = FireKeyEngine()
    last_status = None
    last_attempt = 0.0

    def set_status(text):
        nonlocal last_status
        if text != last_status:
            last_status = text
            write_status(text)

    try:
        while not quit_event.wait(0.5):
            settings = load_settings()
            engine.configure(mode=settings["mode"], trigger=settings["trigger"], target=settings["target"],
                             cps=settings["cps"], double_delay_ms=settings["double_delay_ms"])
            if not settings["enabled"]:
                if engine.running:
                    engine.stop()
                set_status("idle")
                continue
            if engine.running:
                set_status("ok")
            elif time.time() - last_attempt >= 3.0:  # coba lagi berkala (mis. mouse dicolok ulang)
                last_attempt = time.time()
                try:
                    engine.start()
                    set_status("ok")
                except Exception as exception:
                    set_status("error: %s" % exception)
    finally:
        engine.stop()
        clear_status()
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        sys.exit(run_daemon())
    elif "--stop" in sys.argv:
        stop_daemon()
    else:
        print(__doc__)
