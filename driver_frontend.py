import driver_backend
import fire_key
import signal
import gi
import configparser
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

driver_api = driver_backend.DriverApi

MD3_CSS = b"""
/* Minimalist Clean White & Grey - Crisp Text */
* {
    font-family: "Sans";
}

window, window.background {
    background-color: #f5f5f7;
    color: #1d1d1f;
    font-size: 13px;
}

label, button, headerbar, .titlebar {
    color: #1d1d1f;
    text-shadow: none;
    -gtk-icon-shadow: none;
}

headerbar, .titlebar {
    background-color: #f5f5f7;
    background-image: none;
    border-bottom: 1px solid #d1d1d6;
    box-shadow: none;
    padding: 8px 16px;
}

headerbar .title, .card-title {
    font-weight: 600;
    font-size: 14px;
    color: #1d1d1f;
}

/* StackSwitcher (Tabs Header) */
stackswitcher {
    background-color: #e5e5ea;
    border: 1px solid #d1d1d6;
    border-radius: 0px;
    padding: 0px;
}
stackswitcher button {
    background: #ffffff;
    border: none;
    border-right: 1px solid #d1d1d6;
    border-radius: 0px;
    padding: 6px 14px;
    color: #3a3a3c;
    font-weight: 500;
}
stackswitcher button:last-child {
    border-right: none;
}
stackswitcher button:checked {
    background-color: #2c2c2e;
    color: #ffffff;
}
stackswitcher button label {
    color: inherit;
}

/* Cards */
.card-frame {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 0px;
    padding: 16px;
    margin: 8px 12px;
}

.profile-card {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 0px;
    padding: 12px 6px;
}
.profile-card:hover {
    border-color: #8e8e93;
}
.profile-card.active-profile {
    background-color: #fafafc;
    border: 2px solid #2c2c2e;
}

.dpi-badge {
    background-color: #e5e5ea;
    color: #1d1d1f;
    font-weight: 700;
    font-size: 12px;
    border-radius: 0px;
    padding: 3px 8px;
}
.profile-card.active-profile .dpi-badge {
    background-color: #2c2c2e;
    color: #ffffff;
}

.profile-card label, checkbutton label {
    color: #1d1d1f;
    font-weight: 600;
}

/* Sliders */
scale trough {
    background-color: #e5e5ea;
    border-radius: 0px;
    min-width: 6px;
    min-height: 120px;
}
scale highlight {
    background-color: #2c2c2e;
    border-radius: 0px;
}
scale slider {
    background-color: #2c2c2e;
    border-radius: 0px;
    min-width: 16px;
    min-height: 16px;
}

/* Buttons */
button {
    background-image: none;
    background-color: #ffffff;
    color: #1d1d1f;
    border: 1px solid #d1d1d6;
    border-radius: 0px;
    padding: 6px 16px;
    box-shadow: none;
}
button label {
    color: inherit;
}
button:hover {
    background-color: #f2f2f7;
    border-color: #8e8e93;
}
button:active {
    background-color: #e5e5ea;
}

button.primary-btn {
    background-color: #2c2c2e;
    color: #ffffff;
    border: none;
    border-radius: 0px;
    padding: 6px 16px;
    font-weight: 500;
}
button.primary-btn label {
    color: #ffffff;
}
button.primary-btn:hover {
    background-color: #1a1a1c;
}

button.secondary-btn {
    background-color: #ffffff;
    color: #1d1d1f;
    border: 1px solid #d1d1d6;
    border-radius: 0px;
    padding: 6px 16px;
    font-weight: 500;
}
button.secondary-btn label {
    color: #1d1d1f;
}
button.secondary-btn:hover {
    background-color: #f2f2f7;
}

actionbar button {
    background-color: #ffffff;
    color: #1d1d1f;
    border: 1px solid #d1d1d6;
    border-radius: 0px;
    padding: 6px 16px;
}
actionbar button label {
    color: #1d1d1f;
}

/* Combos & Spin buttons */
combobox button, spinbutton, spinbutton entry {
    background-color: #ffffff;
    color: #1d1d1f;
    border: 1px solid #d1d1d6;
    border-radius: 0px;
    padding: 4px 8px;
}

/* Switches */
switch {
    background-color: #d1d1d6;
    border-radius: 0px;
    min-width: 40px;
    min-height: 20px;
}
switch slider {
    border-radius: 0px;
}
switch:checked {
    background-color: #2c2c2e;
}

/* Bottom Action Bar */
actionbar {
    background-color: #f5f5f7;
    border-top: 1px solid #d1d1d6;
    padding: 8px 16px;
}
"""


def apply_custom_theme():
    settings = Gtk.Settings.get_default()
    if settings:
        settings.set_property("gtk-application-prefer-dark-theme", False)
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(MD3_CSS)
    screen = Gdk.Screen.get_default()
    if screen:
        Gtk.StyleContext.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


class driver_frontend(Gtk.Window, driver_api):
    def __init__(self):
        super(driver_frontend, self).__init__()
        super(driver_api, self).__init__()

        apply_custom_theme()

        self.set_title("Fantech X9 Thor Driver")
        self.set_default_size(720, 680)

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

        # Fire Key
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

        # Main Layout VBox
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self.main_box)

        # Header Stack Switcher (Tabs) - Full Width
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)

        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.stack)
        self.stack_switcher.set_hexpand(True)
        self.stack_switcher.set_halign(Gtk.Align.FILL)

        switcher_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        switcher_box.set_margin_top(12)
        switcher_box.set_margin_bottom(8)
        switcher_box.set_margin_start(12)
        switcher_box.set_margin_end(12)
        switcher_box.pack_start(self.stack_switcher, True, True, 0)
        self.main_box.pack_start(switcher_box, False, False, 0)

        # Build Pages
        self.page_dpi = self.build_dpi_page()
        self.page_buttons = self.build_buttons_page()
        self.page_lighting = self.build_lighting_page()
        self.page_firekey = self.build_firekey_page()

        self.stack.add_titled(self.page_dpi, "dpi", "DPI & Profiles")
        self.stack.add_titled(self.page_buttons, "buttons", "Button Mapping")
        self.stack.add_titled(self.page_lighting, "lighting", "RGB Lighting")
        self.stack.add_titled(self.page_firekey, "firekey", "Fire Key Macro")

        for child in self.stack_switcher.get_children():
            child.set_hexpand(True)

        self.main_box.pack_start(self.stack, True, True, 0)

        # Footer Action Bar
        self.action_bar = Gtk.ActionBar()
        self.main_box.pack_end(self.action_bar, False, False, 0)

        self.reconfigure_button = Gtk.Button(label="Reconfigure Device")
        self.reconfigure_button.get_style_context().add_class("secondary-btn")
        self.reconfigure_button.connect("clicked", self.reconfigure_button_clicked)
        self.action_bar.pack_start(self.reconfigure_button)

        self.save_button = Gtk.Button(label="Save Config")
        self.save_button.get_style_context().add_class("secondary-btn")
        self.save_button.connect("clicked", self.on_save_button_clicked)
        self.action_bar.pack_end(self.save_button)

        self.apply_button = Gtk.Button(label="Apply to Mouse")
        self.apply_button.get_style_context().add_class("primary-btn")
        self.apply_button.connect("clicked", self.on_apply_button_clicked)
        self.action_bar.pack_end(self.apply_button)

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.on_quit_signal)

    # --------------------------------------------------------------------------
    # PAGE BUILDERS
    # --------------------------------------------------------------------------
    def build_dpi_page(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        container.set_border_width(20)

        title_label = Gtk.Label(label="DPI Profile Configuration")
        title_label.set_halign(Gtk.Align.START)
        title_label.get_style_context().add_class("card-title")
        container.pack_start(title_label, False, False, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        container.pack_start(hbox, True, True, 0)

        last_index = len(self.supported_dpis) - 1
        self.dpi_scroll_acc = [0.0 for _ in range(6)]
        self.dpis = []
        self.profile_state = []
        self.profile_name = []
        self.active_profiles = []
        self.profile_cards = []
        self.dpi_badges = []

        self.profile_color_container = [Gdk.RGBA() for _ in range(6)]
        self.set_default_colors()
        self.colors = []

        for i in range(6):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            card.get_style_context().add_class("profile-card")
            if i == (self.current_active_profile - 1):
                card.get_style_context().add_class("active-profile")
            self.profile_cards.append(card)

            # Profile Header Radio & Label
            top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            top_box.set_halign(Gtk.Align.CENTER)

            radio = Gtk.RadioButton()
            if i > 0:
                radio.join_group(self.active_profiles[0])
            self.active_profiles.append(radio)
            radio.connect("toggled", self.on_active_profile_toggled, i)
            top_box.pack_start(radio, False, False, 0)

            lbl = Gtk.Label(label=f"P{i + 1}")
            lbl.get_style_context().add_class("card-title")
            top_box.pack_start(lbl, False, False, 0)

            card.pack_start(top_box, False, False, 0)

            # DPI Value Badge
            badge = Gtk.Label(label=f"{self.profile_dpi_configs[i]} DPI")
            badge.get_style_context().add_class("dpi-badge")
            self.dpi_badges.append(badge)
            card.pack_start(badge, False, False, 0)

            # DPI Vertical Scale
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, last_index, 1)
            scale.set_inverted(True)
            scale.set_draw_value(False)
            scale.set_value(self.dpi_to_index(self.profile_dpi_configs[i]))
            scale.connect("scroll-event", self.on_dpi_scrolled, i)
            scale.connect("value-changed", self.on_dpi_changed, i)
            self.dpis.append(scale)
            card.pack_start(scale, True, True, 0)

            # Color Picker
            color_btn = Gtk.ColorButton()
            color_btn.connect("color-set", self.on_color_changed, i)
            color_btn.set_rgba(self.profile_color_container[i])
            self.colors.append(color_btn)
            card.pack_start(color_btn, False, False, 0)

            # Enable/Disable Checkbox
            chk = Gtk.CheckButton(label="Enable")
            chk.set_active(True if self.profile_states[i] == 1 else False)
            chk.connect("toggled", self.on_state_toggled, i)
            chk.set_halign(Gtk.Align.CENTER)
            self.profile_state.append(chk)
            card.pack_start(chk, False, False, 0)

            hbox.pack_start(card, True, True, 0)

            # Sync initial DPI
            self.profile_dpi_configs[i] = self.supported_dpis[int(scale.get_value())]

        self.active_profiles[self.current_active_profile - 1].set_active(True)
        return container

    def build_buttons_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        container.set_border_width(20)
        scrolled.add(container)

        # Section 1: Button Mapping Card
        card_buttons = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_buttons.get_style_context().add_class("card-frame")
        container.pack_start(card_buttons, False, False, 0)

        lbl1 = Gtk.Label(label="Mouse Button Remapping")
        lbl1.set_halign(Gtk.Align.START)
        lbl1.get_style_context().add_class("card-title")
        card_buttons.pack_start(lbl1, False, False, 0)

        self.button_states = ["left", "middle", "right", "forward", "backward"]
        self.button_state_store = Gtk.ListStore(str)
        for st in self.button_states:
            self.button_state_store.append([st])

        grid = Gtk.Grid(column_spacing=16, row_spacing=12)
        card_buttons.pack_start(grid, False, False, 0)

        buttons_def = [
            ("Left Button:", "left", self.on_left_button_state_changed),
            ("Right Button:", "right", self.on_right_button_state_changed),
            ("Middle Button:", "middle", self.on_middle_button_state_changed),
            ("Forward Button:", "forward", self.on_forward_button_state_changed),
            ("Backward Button:", "backward", self.on_backward_button_state_changed)
        ]

        for idx, (label_text, btn_key, cb) in enumerate(buttons_def):
            lbl = Gtk.Label(label=label_text)
            lbl.set_halign(Gtk.Align.START)

            combo = Gtk.ComboBox()
            combo.set_model(self.button_state_store)
            combo.set_active(self.button_states.index(self.current_buttons_state[btn_key]))
            combo.connect("changed", cb)

            renderer = Gtk.CellRendererText()
            combo.pack_start(renderer, True)
            combo.add_attribute(renderer, "text", 0)

            grid.attach(lbl, 0, idx, 1, 1)
            grid.attach(combo, 1, idx, 1, 1)

            if btn_key == "left":
                self.left_button = combo
            elif btn_key == "right":
                self.right_button = combo
            elif btn_key == "middle":
                self.middle_button = combo
            elif btn_key == "forward":
                self.forward_button = combo
            elif btn_key == "backward":
                self.backward_button = combo

        # Section 2: Scroll Wheel Mode Card
        card_wheel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_wheel.get_style_context().add_class("card-frame")
        container.pack_start(card_wheel, False, False, 0)

        lbl2 = Gtk.Label(label="Scroll Wheel Functionality")
        lbl2.set_halign(Gtk.Align.START)
        lbl2.get_style_context().add_class("card-title")
        card_wheel.pack_start(lbl2, False, False, 0)

        hbox_wheel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        card_wheel.pack_start(hbox_wheel, False, False, 0)

        lbl_wheel = Gtk.Label(label="Scroll Wheel Mode:")
        hbox_wheel.pack_start(lbl_wheel, False, False, 0)

        self.scrollwheel_states = ["Volume", "Scroll"]
        self.scrollwheel_state_store = Gtk.ListStore(str)
        for st in self.scrollwheel_states:
            self.scrollwheel_state_store.append([st])

        self.scrollwheel = Gtk.ComboBox()
        self.scrollwheel.set_model(self.scrollwheel_state_store)
        self.scrollwheel.set_active(self.scrollwheel_states.index(self.current_scrollwheel_state))
        self.scrollwheel.connect("changed", self.on_scrollwheel_state_changed)
        renderer = Gtk.CellRendererText()
        self.scrollwheel.pack_start(renderer, True)
        self.scrollwheel.add_attribute(renderer, "text", 0)
        hbox_wheel.pack_start(self.scrollwheel, True, True, 0)

        return scrolled

    def build_lighting_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        container.set_border_width(20)
        scrolled.add(container)

        # Section 1: Color Scheme Card
        card_scheme = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_scheme.get_style_context().add_class("card-frame")
        container.pack_start(card_scheme, False, False, 0)

        lbl_scheme = Gtk.Label(label="RGB Lighting Effects")
        lbl_scheme.set_halign(Gtk.Align.START)
        lbl_scheme.get_style_context().add_class("card-title")
        card_scheme.pack_start(lbl_scheme, False, False, 0)

        grid_scheme = Gtk.Grid(column_spacing=16, row_spacing=12)
        card_scheme.pack_start(grid_scheme, False, False, 0)

        lbl_mode = Gtk.Label(label="Color Scheme Mode:")
        lbl_mode.set_halign(Gtk.Align.START)
        grid_scheme.attach(lbl_mode, 0, 0, 1, 1)

        self.schemes = ["Fixed", "Cyclic", "Static", "Off"]
        self.color_schemes = Gtk.ListStore(str)
        for scheme in self.schemes:
            self.color_schemes.append([scheme])

        self.scheme_combo = Gtk.ComboBox()
        self.scheme_combo.set_model(self.color_schemes)
        self.scheme_combo.set_active(self.schemes.index(self.rgb_color_change_scheme))
        self.scheme_combo.connect("changed", self.on_scheme_changed)
        renderer = Gtk.CellRendererText()
        self.scheme_combo.pack_start(renderer, True)
        self.scheme_combo.add_attribute(renderer, "text", 0)
        grid_scheme.attach(self.scheme_combo, 1, 0, 1, 1)

        lbl_timer = Gtk.Label(label="Effect Duration / Speed:")
        lbl_timer.set_halign(Gtk.Align.START)
        grid_scheme.attach(lbl_timer, 0, 1, 1, 1)

        self.scheme_timers = [1, 2, 3, 4, 5, 6]
        self.color_scheme_timers = Gtk.ListStore(int)
        for timer in self.scheme_timers:
            self.color_scheme_timers.append([timer])

        self.scheme_timer_combo = Gtk.ComboBox()
        self.scheme_timer_combo.set_model(self.color_scheme_timers)
        self.scheme_timer_combo.connect("changed", self.on_current_scheme_timer_changed)
        self.scheme_timer_combo.set_active(self.scheme_timers.index(self.current_scheme_timer))
        renderer2 = Gtk.CellRendererText()
        self.scheme_timer_combo.pack_start(renderer2, True)
        self.scheme_timer_combo.add_attribute(renderer2, "text", 0)
        grid_scheme.attach(self.scheme_timer_combo, 1, 1, 1, 1)

        # Section 2: Cyclic Colors Selection Card
        card_cyclic = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_cyclic.get_style_context().add_class("card-frame")
        container.pack_start(card_cyclic, False, False, 0)

        lbl_cyc_title = Gtk.Label(label="Active Cyclic Colors")
        lbl_cyc_title.set_halign(Gtk.Align.START)
        lbl_cyc_title.get_style_context().add_class("card-title")
        card_cyclic.pack_start(lbl_cyc_title, False, False, 0)

        flowbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card_cyclic.pack_start(flowbox, False, False, 0)

        self.cyclic_colors_state = []
        for colorname in self.cyclic_colors.keys():
            chk = Gtk.CheckButton(label=colorname)
            chk.set_active(True if self.cyclic_colors[colorname] == 1 else False)
            chk.connect("toggled", self.on_cyclic_color_changed)
            self.cyclic_colors_state.append(chk)
            flowbox.pack_start(chk, True, True, 0)

        return scrolled

    def build_firekey_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        container.set_border_width(20)
        scrolled.add(container)

        # Card Frame
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        card.get_style_context().add_class("card-frame")
        container.pack_start(card, False, False, 0)

        # Header Switch
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card.pack_start(switch_box, False, False, 0)

        title = Gtk.Label(label="Software Fire Key / Auto-Clicker")
        title.set_halign(Gtk.Align.START)
        title.get_style_context().add_class("card-title")
        switch_box.pack_start(title, True, True, 0)

        self.fire_key_switch = Gtk.Switch()
        self.fire_key_switch.set_active(self.fire_key_enabled)
        self.fire_key_switch.connect("notify::active", self.on_fire_key_switch_toggled)
        switch_box.pack_end(self.fire_key_switch, False, False, 0)

        # Configuration Grid
        self.fire_grid = Gtk.Grid(column_spacing=16, row_spacing=12)
        card.pack_start(self.fire_grid, False, False, 0)

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

        note = Gtk.Label()
        note.set_markup("<small><i>Runs as background daemon via evdev/uinput. Remains active when window is closed.</i></small>")
        note.set_halign(Gtk.Align.START)
        card.pack_start(note, False, False, 0)

        return scrolled

    # --------------------------------------------------------------------------
    # EVENT HANDLERS & LOGIC
    # --------------------------------------------------------------------------
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
            with open(self.config_location, "r") as file:
                pass
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

    def on_fire_key_switch_toggled(self, switch, param):
        self.fire_key_enabled = switch.get_active()
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
        if hasattr(self, 'fire_key_switch'):
            self.fire_key_switch.set_active(False)

    def reconfigure_button_clicked(self, button):
        self.startup()

    def on_state_toggled(self, button, profile):
        state = button.get_active()
        self.profile_states[profile] = 1 if state else 0

    def on_active_profile_toggled(self, button, profile):
        if button.get_active():
            self.current_active_profile = profile + 1
            for idx, card in enumerate(self.profile_cards):
                if idx == profile:
                    card.get_style_context().add_class("active-profile")
                else:
                    card.get_style_context().remove_class("active-profile")

    def on_current_scheme_timer_changed(self, combo):
        timer = combo.get_active()
        if timer >= 0:
            self.current_scheme_timer = timer + 1

    def on_scrollwheel_state_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter:
            model = combo.get_model()
            self.current_scrollwheel_state = model[tree_iter][0]

    def on_button_state_changed(self, combo, button_name):
        tree_iter = combo.get_active_iter()
        if tree_iter:
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

        for btn in self.current_buttons_state.keys():
            config = self.create_button_config(btn, self.current_buttons_state[btn])
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
                self.dpi_scroll_acc[profile] += -dy
                if abs(self.dpi_scroll_acc[profile]) >= 1:
                    step = 1 if self.dpi_scroll_acc[profile] > 0 else -1
                    self.dpi_scroll_acc[profile] = 0.0
        if step:
            index = int(round(scale.get_value())) + step
            index = max(0, min(len(self.supported_dpis) - 1, index))
            scale.set_value(index)
        return True

    def on_dpi_changed(self, scale, profile):
        index = max(0, min(len(self.supported_dpis) - 1, int(round(scale.get_value()))))
        dpi_val = self.supported_dpis[index]
        self.profile_dpi_configs[profile] = dpi_val
        if hasattr(self, 'dpi_badges') and profile < len(self.dpi_badges):
            self.dpi_badges[profile].set_label(f"{dpi_val} DPI")

    def on_color_changed(self, color, profile):
        self.profile_color_container[profile] = color.get_rgba()
        self.profile_color_configs[profile] = color.get_rgba().to_string()

    def on_cyclic_color_changed(self, button):
        label = button.get_label()
        state = button.get_active()
        if label:
            self.cyclic_colors[label] = 1 if state else 0

    def on_save_button_clicked(self, button):
        self.save_configs()

    def set_default_colors(self):
        for i in range(6):
            self.profile_color_container[i].parse(self.profile_color_configs[i])

    def on_scheme_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if not tree_iter:
            return
        model = combo.get_model()
        self.rgb_color_change_scheme = model[tree_iter][0]

        time_not_req = ["Static", "Off"]
        if self.rgb_color_change_scheme in time_not_req:
            self.scheme_timer_combo.set_sensitive(False)
        else:
            self.scheme_timer_combo.set_sensitive(True)
            self.scheme_timer_combo.set_model(self.color_scheme_timers)
            self.scheme_timer_combo.set_active(self.scheme_timers.index(self.current_scheme_timer))


if __name__ == "__main__":
    ui = driver_frontend()
    ui.show_all()
    ui.connect("destroy", Gtk.main_quit)
    Gtk.main()
