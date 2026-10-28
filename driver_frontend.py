import driver_backend
import fire_key
import signal
import gi
import configparser
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib

driver_api = driver_backend.DriverApi


class driver_frontend(Gtk.Window, driver_api):
    def __init__(self):
        super(driver_frontend, self).__init__()
        super(driver_api, self).__init__()
        self.set_title("FantechX9Thor")
        self.set_default_size(500, 800)

        ########################################################################
        # Default Configs
        self.profile_dpi_configs = [200, 600, 1000, 1600, 2400, 4000]
        self.profile_states = [1, 1, 1, 1, 1, 1]
        self.profile_color_configs = [
            "rgb(255,255,0)",
            "rgb(0,0,255)",
            "rgb(255,0,255)",
            "rgb(0,255,0)",
            "rgb(255,0,0)",
            "rgb(0,255,255)"
        ]
        self.current_active_profile = 3
        self.rgb_color_change_scheme = "Cyclic"
        self.current_scheme_timer = 1
        self.current_scrollwheel_state = "Scroll"
        self.current_buttons_state = {
            "left": "left",
            "right": "right",
            "middle": "middle",
            "forward": "forward",
            "backward": "backward"
        }

        # Fire Key (software, via evdev/uinput - lihat fire_key.py)
        # Berjalan sebagai daemon terpisah, jadi tetap aktif walau GUI ditutup.
        # Pengaturan disimpan di ~/.config/fantech-x9/fire_key.conf
        fire = fire_key.load_settings()
        self.fire_key_enabled = fire_key.daemon_pid() is not None
        self.fire_key_mode = fire["mode"]
        self.fire_key_trigger = fire["trigger"]
        self.fire_key_target = fire["target"]
        self.fire_key_cps = fire["cps"]
        self.fire_key_delay = fire["double_delay_ms"]

        self.cyclic_colors = {"Yellow": 1, "Blue": 1, "Violet": 1, "Green": 1, "Red": 1, "Cyan": 1, "White": 1}
        ########################################################################

        self.config_location = "driver.conf"
        self.startup()

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(self.vbox)

        # Slider bekerja di index list supported_dpis (0..11), jadi cuma bisa
        # berhenti di DPI yang valid. Scroll mouse = naik/turun satu step.
        last_index = len(self.supported_dpis) - 1
        self.dpi_scroll_acc = [0.0 for _ in range(6)]
        self.dpis = [Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, last_index, 1) for _ in range(6)]
        for i in range(6):
            self.dpis[i].set_inverted(True)
            self.dpis[i].set_digits(0)
            self.dpis[i].set_round_digits(0)
            self.dpis[i].set_value_pos(Gtk.PositionType.TOP)
            self.dpis[i].set_value(self.dpi_to_index(self.profile_dpi_configs[i]))
            self.dpis[i].connect("format-value", self.on_dpi_format)
            self.dpis[i].connect("scroll-event", self.on_dpi_scrolled, i)
            self.dpis[i].connect("value-changed", self.on_dpi_changed, i)
            for index in range(len(self.supported_dpis)):
                self.dpis[i].add_mark(index, Gtk.PositionType.LEFT)
            # sinkronkan nilai awal (mis. dari config lama yang nilainya tidak valid)
            self.profile_dpi_configs[i] = self.supported_dpis[int(self.dpis[i].get_value())]

        self.profile_state = [Gtk.CheckButton() for _ in range(6)]
        for i in range(6):
            self.profile_state[i].set_active(True if self.profile_states[i] == 1 else False)
            self.profile_state[i].connect("toggled", self.on_state_toggled, i)
            self.profile_state[i].set_halign(Gtk.Align.CENTER)

        self.profile_name = [Gtk.Label() for _ in range(6)]
        for i in range(6):
            label = "Profile " + str(i + 1)
            self.profile_name[i].set_label(label)

        self.active_profiles = [Gtk.RadioButton() for _ in range(6)]
        for i in range(6):
            self.active_profiles[i].join_group(self.active_profiles[0])
            self.active_profiles[i].set_halign(Gtk.Align.CENTER)
            self.active_profiles[i].connect("toggled", self.on_active_profile_toggled, i)
        self.active_profiles[self.current_active_profile - 1].set_active(True)

        self.profile_color_container = [Gdk.RGBA() for _ in range(6)]
        self.set_default_colors()
        self.colors = [Gtk.ColorButton() for _ in range(6)]
        for i in range(6):
            self.colors[i].connect("color-set", self.on_color_changed, i)
            self.colors[i].set_rgba(self.profile_color_container[i])

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.vbox.pack_start(self.hbox, True, True, 0)

        self.profiles = [Gtk.VBox(spacing=6) for _ in range(6)]

        for i in range(6):
            self.hbox.pack_start(self.profiles[i], True, True, 0)
            self.profiles[i].pack_start(self.dpis[i], True, True, 10)
            self.profiles[i].pack_start(self.profile_state[i], False, True, 0)
            self.profiles[i].pack_start(self.profile_name[i], False, True, 0)
            self.profiles[i].pack_start(self.active_profiles[i], False, True, 0)
            self.profiles[i].pack_start(self.colors[i], False, False, 0)

        self.schemes = ["Fixed", "Cyclic", "Static", "Off"]
        self.color_schemes = Gtk.ListStore(str)
        for scheme in self.schemes:
            self.color_schemes.append([scheme])

        self.scheme_timers = [1, 2, 3, 4, 5, 6]
        self.color_scheme_timers = Gtk.ListStore(int)
        for timer in self.scheme_timers:
            self.color_scheme_timers.append([timer])

        self.hbox_color_scheme = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.vbox.pack_start(self.hbox_color_scheme, False, False, 20)

        self.scheme_combo_label = Gtk.Label()
        self.scheme_combo_label.set_label("Color Scheme:")
        self.hbox_color_scheme.pack_start(self.scheme_combo_label, False, False, 0)
        self.scheme_combo = Gtk.ComboBox()
        self.scheme_combo.set_model(self.color_schemes)
        self.scheme_combo.set_active(self.schemes.index(self.rgb_color_change_scheme))
        self.scheme_combo.connect("changed", self.on_scheme_changed)
        self.hbox_color_scheme.pack_start(self.scheme_combo, True, True, 0)
        self.renderer_text = Gtk.CellRendererText()
        self.scheme_combo.pack_start(self.renderer_text, True)
        self.scheme_combo.add_attribute(self.renderer_text, "text", 0)

        self.scheme_timer_label = Gtk.Label()
        self.scheme_timer_label.set_label("Scheme Timer:")
        self.hbox_color_scheme.pack_start(self.scheme_timer_label, False, False, 0)
        self.scheme_timer_combo = Gtk.ComboBox()
        self.scheme_timer_combo.set_model(self.color_scheme_timers)
        self.scheme_timer_combo.connect("changed", self.on_current_scheme_timer_changed)
        self.scheme_timer_combo.set_active(self.scheme_timers.index(self.current_scheme_timer))
        self.hbox_color_scheme.pack_start(self.scheme_timer_combo, True, True, 0)
        self.renderer_text = Gtk.CellRendererText()
        self.scheme_timer_combo.pack_start(self.renderer_text, True)
        self.scheme_timer_combo.add_attribute(self.renderer_text, "text", 0)

        self.button_config_label = Gtk.Label()
        self.button_config_label.set_label("Button config:")
        self.button_config_label.set_halign(Gtk.Align.START)
        self.vbox.pack_start(self.button_config_label, False, True, 0)

        # Scroll wheel Functionality
        self.scrollwheel_states = ["Volume", "Scroll"]
        self.scrollwheel_state = Gtk.ListStore(str)
        for state in self.scrollwheel_states:
            self.scrollwheel_state.append([state])

        self.hbox_wheel_func = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.vbox.pack_start(self.hbox_wheel_func, False, False, 0)

        self.scrollwheel_label = Gtk.Label()
        self.scrollwheel_label.set_label("Scroll wheel:")
        self.hbox_wheel_func.pack_start(self.scrollwheel_label, False, False, 0)

        self.scrollwheel = Gtk.ComboBox()
        self.scrollwheel.set_model(self.scrollwheel_state)
        self.scrollwheel.set_active(self.scrollwheel_states.index(self.current_scrollwheel_state))
        self.scrollwheel.connect("changed", self.on_scrollwheel_state_changed)
        self.hbox_wheel_func.pack_start(self.scrollwheel, True, True, 0)

        self.scrollwheel_renderer_text = Gtk.CellRendererText()
        self.scrollwheel.pack_start(self.scrollwheel_renderer_text, True)
        self.scrollwheel.add_attribute(self.scrollwheel_renderer_text, "text", 0)

        # Button Functionality
        self.button_states = ["left", "middle", "right", "forward", "backward"]

        self.button_state = Gtk.ListStore(str)
        for state in self.button_states:
            self.button_state.append([state])

        # Left Button Functionality
        self.hbox_left_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.vbox.pack_start(self.hbox_left_button, False, False, 0)

        self.left_button_label = Gtk.Label()
        self.left_button_label.set_label("Left Button:")
        self.hbox_left_button.pack_start(self.left_button_label, False, False, 0)

        self.left_button = Gtk.ComboBox()
        self.left_button.set_model(self.button_state)
        self.left_button.set_active(self.button_states.index(self.current_buttons_state["left"]))
        self.left_button.connect("changed", self.on_left_button_state_changed)
        self.hbox_left_button.pack_start(self.left_button, True, True, 0)

        self.left_button_renderer_text = Gtk.CellRendererText()
        self.left_button.pack_start(self.left_button_renderer_text, True)
        self.left_button.add_attribute(self.left_button_renderer_text, "text", 0)

        # Middle Button Functionality
        self.hbox_middle_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.vbox.pack_start(self.hbox_middle_button, False, False, 0)

        self.middle_button_label = Gtk.Label()
        self.middle_button_label.set_label("Middle Button:")
        self.hbox_middle_button.pack_start(self.middle_button_label, False, False, 0)

        self.middle_button = Gtk.ComboBox()
        self.middle_button.set_model(self.button_state)
        self.middle_button.set_active(self.button_states.index(self.current_buttons_state["middle"]))
        self.middle_button.connect("changed", self.on_middle_button_state_changed)
        self.hbox_middle_button.pack_start(self.middle_button, True, True, 0)

        self.middle_button_renderer_text = Gtk.CellRendererText()
        self.middle_button.pack_start(self.middle_button_renderer_text, True)
        self.middle_button.add_attribute(self.middle_button_renderer_text, "text", 0)

        # Right Button Functionality
        self.hbox_right_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.vbox.pack_start(self.hbox_right_button, False, False, 0)

        self.right_button_label = Gtk.Label()
        self.right_button_label.set_label("Right Button:")
        self.hbox_right_button.pack_start(self.right_button_label, False, False, 0)

        self.right_button = Gtk.ComboBox()
        self.right_button.set_model(self.button_state)
        self.right_button.set_active(self.button_states.index(self.current_buttons_state["right"]))
        self.right_button.connect("changed", self.on_right_button_state_changed)
        self.hbox_right_button.pack_start(self.right_button, True, True, 0)

        self.right_button_renderer_text = Gtk.CellRendererText()
        self.right_button.pack_start(self.right_button_renderer_text, True)
        self.right_button.add_attribute(self.right_button_renderer_text, "text", 0)

        # Forward Button Functionality
        self.hbox_forward_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.vbox.pack_start(self.hbox_forward_button, False, False, 0)

        self.forward_button_label = Gtk.Label()
        self.forward_button_label.set_label("Forward Button:")
        self.hbox_forward_button.pack_start(self.forward_button_label, False, False, 0)

        self.forward_button = Gtk.ComboBox()
        self.forward_button.set_model(self.button_state)
        self.forward_button.set_active(self.button_states.index(self.current_buttons_state["forward"]))
        self.forward_button.connect("changed", self.on_forward_button_state_changed)
        self.hbox_forward_button.pack_start(self.forward_button, True, True, 0)

        self.forward_button_renderer_text = Gtk.CellRendererText()
        self.forward_button.pack_start(self.forward_button_renderer_text, True)
        self.forward_button.add_attribute(self.forward_button_renderer_text, "text", 0)

        # Backward Button Functionality
        self.hbox_backward_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.vbox.pack_start(self.hbox_backward_button, False, False, 0)

        self.backward_button_label = Gtk.Label()
        self.backward_button_label.set_label("Backward Button:")
        self.hbox_backward_button.pack_start(self.backward_button_label, False, False, 0)

        self.backward_button = Gtk.ComboBox()
        self.backward_button.set_model(self.button_state)
        self.backward_button.set_active(self.button_states.index(self.current_buttons_state["backward"]))
        self.backward_button.connect("changed", self.on_backward_button_state_changed)
        self.hbox_backward_button.pack_start(self.backward_button, True, True, 0)

        self.backward_button_renderer_text = Gtk.CellRendererText()
        self.backward_button.pack_start(self.backward_button_renderer_text, True)
        self.backward_button.add_attribute(self.backward_button_renderer_text, "text", 0)

        self.cyclic_colors_label = Gtk.Label()
        self.cyclic_colors_label.set_margin_top(20)
        self.cyclic_colors_label.set_label("Colors active during cyclic color change:")
        self.cyclic_colors_label.set_halign(Gtk.Align.START)
        self.vbox.pack_start(self.cyclic_colors_label, False, True, 0)

        self.hbox_cyclic_color_state = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.vbox.pack_start(self.hbox_cyclic_color_state, False, True, 0)
        self.cyclic_colors_state = [Gtk.CheckButton() for _ in range(len(self.cyclic_colors))]
        prof = 0
        for colorname in self.cyclic_colors.keys():
            self.cyclic_colors_state[prof].set_label(colorname)
            self.cyclic_colors_state[prof].set_active(True if self.cyclic_colors[colorname] == 1 else False)
            self.cyclic_colors_state[prof].connect("toggled", self.on_cyclic_color_changed)
            self.hbox_cyclic_color_state.pack_start(self.cyclic_colors_state[prof], True, True, 0)
            prof += 1

        # Fire Key
        self.fire_key_label = Gtk.Label()
        self.fire_key_label.set_margin_top(20)
        self.fire_key_label.set_label("Fire Key (software):")
        self.fire_key_label.set_halign(Gtk.Align.START)
        self.vbox.pack_start(self.fire_key_label, False, True, 0)

        self.fire_key_check = Gtk.CheckButton(label="Enable Fire Key")
        self.fire_key_check.set_active(self.fire_key_enabled)
        self.fire_key_check.connect("toggled", self.on_fire_key_toggled)
        self.vbox.pack_start(self.fire_key_check, False, True, 0)

        self.fire_grid = Gtk.Grid(column_spacing=6, row_spacing=6)
        self.vbox.pack_start(self.fire_grid, False, False, 0)

        self.fire_mode_combo = self.make_fire_combo(fire_key.MODES, self.fire_key_mode,
                                                    self.on_fire_mode_changed)
        self.fire_trigger_combo = self.make_fire_combo(fire_key.BUTTONS, self.fire_key_trigger,
                                                       self.on_fire_trigger_changed)
        self.fire_target_combo = self.make_fire_combo(fire_key.BUTTONS, self.fire_key_target,
                                                      self.on_fire_target_changed)

        self.fire_cps_spin = Gtk.SpinButton.new_with_range(1, 50, 1)
        self.fire_cps_spin.set_value(self.fire_key_cps)
        self.fire_cps_spin.connect("value-changed", self.on_fire_cps_changed)

        self.fire_delay_spin = Gtk.SpinButton.new_with_range(5, 100, 5)
        self.fire_delay_spin.set_value(self.fire_key_delay)
        self.fire_delay_spin.connect("value-changed", self.on_fire_delay_changed)

        rows = [("Mode:", self.fire_mode_combo),
                ("Trigger button:", self.fire_trigger_combo),
                ("Output click:", self.fire_target_combo),
                ("Auto click (clicks/sec):", self.fire_cps_spin),
                ("Double click delay (ms):", self.fire_delay_spin)]
        for row, (text, widget) in enumerate(rows):
            label = Gtk.Label(label=text)
            label.set_halign(Gtk.Align.START)
            widget.set_hexpand(True)
            self.fire_grid.attach(label, 0, row, 1, 1)
            self.fire_grid.attach(widget, 1, row, 1, 1)

        self.fire_key_note = Gtk.Label()
        self.fire_key_note.set_label("Tetap aktif di background walau jendela ini ditutup.")
        self.fire_key_note.set_halign(Gtk.Align.START)
        self.vbox.pack_start(self.fire_key_note, False, True, 0)

        # Ctrl+C menutup GUI saja, Fire Key (daemon) tidak ikut berhenti
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.on_quit_signal)

        self.action_bar = Gtk.ActionBar()
        self.vbox.pack_end(self.action_bar, False, False, 0)

        self.apply_button = Gtk.Button()
        self.apply_button.set_label("Apply")
        self.apply_button.connect("clicked", self.on_apply_button_clicked)
        self.action_bar.pack_end(self.apply_button)

        self.reconfigure_button = Gtk.Button()
        self.reconfigure_button.set_label("Reconfigure Device")
        self.reconfigure_button.connect("clicked", self.reconfigure_button_clicked)
        self.action_bar.pack_start(self.reconfigure_button)

        self.save_button = Gtk.Button()
        self.save_button.set_label("Save Config")
        self.save_button.connect("clicked", self.on_save_button_clicked)
        self.action_bar.pack_end(self.save_button)

    def startup(self):
        self.find_device()
        state = self.device_state()
        alert = Gtk.MessageDialog()
        alert.add_button("Close", Gtk.ResponseType.CLOSE)
        alert.props.use_markup = True
        if state == -1:
            alert.set_markup('''Insufficient Permissions! Try adding a udev rule for your mouse, follow the guide <a 
            href="https://wiki.archlinux.org/index.php/udev
            #Accessing_firmware_programmers_and_USB_virtual_comm_devicesrunning" title="Arch Wiki Guide">here</a>. 
            Running as root will probably work too but not recommended''')
            alert.run()
            alert.destroy()
        elif state == -2:
            alert.set_markup("Device not found! Try Replugging.")
            alert.run()
            alert.destroy()

        try:
            file = open(self.config_location, "r")
            file.close()
            self.retrieve_configs()
        except FileNotFoundError:
            print("Config file not found. Creating...")
            self.save_configs()

    def save_configs(self):
        config = configparser.ConfigParser()

        profiles = ["profile_1", "profile_2", "profile_3", "profile_4", "profile_5", "profile_6"]
        config["Active_Profile"] = {"Profile": self.current_active_profile}
        config["Profile_DPIs"] = dict(zip(profiles, self.profile_dpi_configs))
        config["Profile_States"] = dict(zip(profiles, self.profile_states))
        config["Profile_Colors"] = dict(zip(profiles, self.profile_color_configs))
        config["Color_Scheme"] = {"type": self.rgb_color_change_scheme, "duration": self.current_scheme_timer}
        config["Cyclic_Colors"] = self.cyclic_colors
        config["Scroll_Wheel"] = {"type": self.current_scrollwheel_state}
        config["Button_Config"] = dict(zip(self.current_buttons_state.keys(), self.current_buttons_state.values()))

        with open(self.config_location, "w") as configfile:
            config.write(configfile)

    def retrieve_configs(self):
        config = configparser.ConfigParser()
        config.read(self.config_location)

        temp_dict = config["Active_Profile"]
        for key, value in temp_dict.items():
            self.current_active_profile = int(value)

            prof = 0
            temp_dict = config["Profile_DPIs"]
        for key, value in temp_dict.items():
            self.profile_dpi_configs[prof] = int(value)
            prof += 1

        prof = 0
        temp_dict = config["Profile_States"]
        for key, value in temp_dict.items():
            self.profile_states[prof] = int(value)
            prof += 1

        prof = 0
        temp_dict = config["Profile_Colors"]
        for key, value in temp_dict.items():
            self.profile_color_configs[prof] = value
            prof += 1

        temp_dict = config["Color_Scheme"]
        self.rgb_color_change_scheme = temp_dict["type"]
        self.current_scheme_timer = int(temp_dict["duration"])

        temp_dict = dict(config["Cyclic_Colors"])
        temp_values = list(temp_dict.values())
        temp_keys = list(temp_dict.keys())
        for prof in range(len(temp_dict)):
            temp_keys[prof] = temp_keys[prof].capitalize()
            self.cyclic_colors[temp_keys[prof]] = int(temp_values[prof])

        temp_dict = config["Scroll_Wheel"]
        self.current_scrollwheel_state = temp_dict["type"]

        temp_dict = config["Button_Config"]
        for key, value in temp_dict.items():
            self.current_buttons_state[key] = value

    def make_fire_combo(self, items, active, callback):
        combo = Gtk.ComboBoxText()
        for item in items:
            combo.append_text(item)
        combo.set_active(items.index(active))
        combo.connect("changed", callback)
        return combo

    def on_fire_key_toggled(self, button):
        self.fire_key_enabled = button.get_active()
        self.apply_fire_key()

    def on_fire_mode_changed(self, combo):
        self.fire_key_mode = combo.get_active_text()
        self.apply_fire_key()

    def on_fire_trigger_changed(self, combo):
        self.fire_key_trigger = combo.get_active_text()
        self.apply_fire_key()

    def on_fire_target_changed(self, combo):
        self.fire_key_target = combo.get_active_text()
        self.apply_fire_key()

    def on_fire_cps_changed(self, spin):
        self.fire_key_cps = spin.get_value_as_int()
        self.apply_fire_key()

    def on_fire_delay_changed(self, spin):
        self.fire_key_delay = spin.get_value_as_int()
        self.apply_fire_key()

    def on_quit_signal(self):
        Gtk.main_quit()
        return False

    def apply_fire_key(self):
        fire_key.save_settings({"enabled": self.fire_key_enabled,
                                "mode": self.fire_key_mode,
                                "trigger": self.fire_key_trigger,
                                "target": self.fire_key_target,
                                "cps": self.fire_key_cps,
                                "double_delay_ms": self.fire_key_delay})
        if not self.fire_key_enabled:
            fire_key.stop_daemon()
            return
        if fire_key.daemon_pid() is None:
            fire_key.clear_status()
            try:
                fire_key.start_daemon()
            except OSError as exception:
                self.show_fire_key_error(str(exception))
                return
            GLib.timeout_add(1500, self.check_fire_key_status)

    def check_fire_key_status(self):
        if not self.fire_key_enabled:
            return False
        status = fire_key.read_status()
        if status.startswith("error"):
            self.show_fire_key_error(status[len("error:"):].strip())
        elif fire_key.daemon_pid() is None:
            self.show_fire_key_error("Daemon langsung berhenti. Cek log: " + fire_key.LOG_FILE)
        return False

    def show_fire_key_error(self, message):
        alert = Gtk.MessageDialog(transient_for=self, message_type=Gtk.MessageType.ERROR,
                                  buttons=Gtk.ButtonsType.CLOSE, text="Fire Key gagal dijalankan")
        alert.format_secondary_text(message)
        alert.run()
        alert.destroy()
        self.fire_key_check.set_active(False)

    def reconfigure_button_clicked(self, button):
        self.startup()

    def on_state_toggled(self, button, profile):
        state = button.get_active()
        if state:
            self.profile_states[profile] = 1
        else:
            self.profile_states[profile] = 0

    def on_active_profile_toggled(self, button, profile):
        if button.get_active():
            self.current_active_profile = profile + 1

    def on_current_scheme_timer_changed(self, radio):
        timer = radio.get_active()
        self.current_scheme_timer = timer + 1

    def on_scrollwheel_state_changed(self, combo):
        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.current_scrollwheel_state = model[tree_iter][0]

    def on_button_state_changed(self, combo, button_name):
        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.current_buttons_state[button_name] = model[tree_iter][0]

    def on_left_button_state_changed(self, combo):
        self.on_button_state_changed(combo, "left")

    def on_right_button_state_changed(self, combo):
        self.on_button_state_changed(combo, "right")

    def on_middle_button_state_changed(self, combo):
        self.on_button_state_changed(combo, "middle")

    def on_forward_button_state_changed(self, combo):
        self.on_button_state_changed(combo, "forward")

    def on_backward_button_state_changed(self, combo):
        self.on_button_state_changed(combo, "backward")

    def on_apply_button_clicked(self, button):
        self.conquer()

        profile = 1
        for dpi in self.profile_dpi_configs:
            config = self.create_dpi_profile_config(dpi, profile)
            self.send_payload(config)
            profile += 1
        profile = 1
        for color in self.profile_color_container:
            red = int(color.red * 255)
            green = int(color.green * 255)
            blue = int(color.blue * 255)
            config = self.create_color_profile_config(profile, red, green, blue)
            self.send_payload(config)
            profile += 1
        config = self.create_rgb_lights_config(self.rgb_color_change_scheme, self.current_scheme_timer)
        self.send_payload(config)

        config = self.create_scrollwheel_config(self.current_scrollwheel_state)
        self.send_payload(config)

        for button in self.current_buttons_state.keys():
            config = self.create_button_config(button, self.current_buttons_state[button])
            self.send_payload(config)

        self.liberate()

    def dpi_to_index(self, dpi):
        return self.supported_dpis.index(self.find_closest_dpi(dpi))

    def on_dpi_format(self, scale, value):
        index = max(0, min(len(self.supported_dpis) - 1, int(round(value))))
        return str(self.supported_dpis[index])

    def on_dpi_scrolled(self, scale, event, profile):
        step = 0
        if event.direction == Gdk.ScrollDirection.UP:
            step = 1
        elif event.direction == Gdk.ScrollDirection.DOWN:
            step = -1
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, dx, dy = event.get_scroll_deltas()
            if ok:
                # akumulasi supaya touchpad tidak melompat banyak step sekaligus
                self.dpi_scroll_acc[profile] += -dy
                if abs(self.dpi_scroll_acc[profile]) >= 1:
                    step = 1 if self.dpi_scroll_acc[profile] > 0 else -1
                    self.dpi_scroll_acc[profile] = 0.0
        if step:
            index = int(round(scale.get_value())) + step
            index = max(0, min(len(self.supported_dpis) - 1, index))
            scale.set_value(index)
        return True  # event habis di sini, tidak diproses bawaan GTK

    def on_dpi_changed(self, scale, profile):
        index = max(0, min(len(self.supported_dpis) - 1, int(round(scale.get_value()))))
        self.profile_dpi_configs[profile] = self.supported_dpis[index]

    def on_color_changed(self, color, profile):
        self.profile_color_container[profile] = color.get_rgba()
        self.profile_color_configs[profile] = color.get_rgba().to_string()

    def on_cyclic_color_changed(self, button):
        label = button.get_label()
        state = button.get_active()
        if state:
            self.cyclic_colors[label] = 1
        else:
            self.cyclic_colors[label] = 0

    def on_save_button_clicked(self, button):
        self.save_configs()

    def set_default_colors(self):
        for i in range(6):
            self.profile_color_container[i].parse(self.profile_color_configs[i])

    def on_scheme_changed(self, combo):
        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.rgb_color_change_scheme = model[tree_iter][0]

        time_not_req = ["Static", "Off"]

        if self.rgb_color_change_scheme in time_not_req:
            self.scheme_timer_combo.set_model()
        else:
            self.scheme_timer_combo.set_model(self.color_scheme_timers)
            self.scheme_timer_combo.set_active(self.scheme_timers.index(self.current_scheme_timer))


ui = driver_frontend()
ui.show_all()
ui.connect("destroy", Gtk.main_quit)
Gtk.main()
