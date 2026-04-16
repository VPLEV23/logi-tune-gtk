"""
main.py — Application entry point.

Initialises the GTK4 / libadwaita app and launches the main window.
"""

import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from mouse import list_devices


APP_ID = "com.github.vplev23.logitune"

PAGES = [
    ("input-mouse-symbolic",  "DPI",          "dpi"),
    ("input-gaming-symbolic", "Buttons",       "buttons"),
    ("speedometer-symbolic",  "Polling Rate",  "polling"),
    ("view-list-symbolic",    "Profiles",      "profiles"),
]


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Logi Tune")
        self.set_default_size(900, 640)

        self._mouse = None
        self._build_ui()
        self._load_devices()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._split_view = Adw.NavigationSplitView()
        self._split_view.set_min_sidebar_width(200)
        self._split_view.set_max_sidebar_width(260)

        # ---- Sidebar ----
        sidebar_page = Adw.NavigationPage(title="Logi Tune")
        sidebar_toolbar = Adw.ToolbarView()
        sidebar_page.set_child(sidebar_toolbar)
        sidebar_toolbar.add_top_bar(Adw.HeaderBar())

        self._device_label = Gtk.Label(label="No device")
        self._device_label.add_css_class("caption")
        self._device_label.add_css_class("dim-label")
        self._device_label.set_margin_start(16)
        self._device_label.set_margin_end(16)
        self._device_label.set_margin_top(8)
        self._device_label.set_xalign(0)
        self._device_label.set_ellipsize(3)

        self._nav_list = Gtk.ListBox()
        self._nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._nav_list.add_css_class("navigation-sidebar")
        self._nav_list.connect("row-selected", self._on_nav_row_selected)

        for icon, label, _ in PAGES:
            self._nav_list.append(self._make_nav_row(icon, label))

        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar_box.append(self._device_label)
        sidebar_box.append(self._nav_list)
        sidebar_toolbar.set_content(sidebar_box)
        self._split_view.set_sidebar(sidebar_page)

        # ---- Content area ----
        self._content_page = Adw.NavigationPage(title="DPI")
        self._content_toolbar = Adw.ToolbarView()
        self._content_page.set_child(self._content_toolbar)
        self._content_toolbar.add_top_bar(Adw.HeaderBar())

        self._content_stack = Gtk.Stack()
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._content_toolbar.set_content(self._content_stack)

        # No-device placeholder
        status = Adw.StatusPage()
        status.set_icon_name("input-mouse-symbolic")
        status.set_title("No mouse detected")
        status.set_description("Make sure ratbagd is running and your mouse is connected.")
        self._content_stack.add_named(status, "no-device")

        # Content pages
        self._content_stack.add_named(self._build_dpi_page(),      "dpi")
        self._content_stack.add_named(self._build_buttons_page(),   "buttons")
        self._content_stack.add_named(self._build_polling_page(),   "polling")
        self._content_stack.add_named(self._build_profiles_page(),  "profiles")

        self._content_stack.set_visible_child_name("no-device")
        self._split_view.set_content(self._content_page)

        root = Adw.ToolbarView()
        root.set_content(self._split_view)
        self.set_content(root)

        self._nav_list.select_row(self._nav_list.get_row_at_index(0))

    def _make_nav_row(self, icon_name, label):
        row = Gtk.ListBoxRow()
        row.set_size_request(-1, 48)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(16)

        lbl = Gtk.Label(label=label)
        lbl.set_xalign(0)
        lbl.set_hexpand(True)

        box.append(icon)
        box.append(lbl)
        row.set_child(box)
        return row

    def _make_content_scroll(self):
        """Scrolled window + centred clamp — shared boilerplate for every page."""
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(600)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)
        scroll.set_child(clamp)
        return scroll, clamp

    # ------------------------------------------------------------------
    # DPI page
    # ------------------------------------------------------------------

    def _build_dpi_page(self):
        scroll, self._dpi_clamp = self._make_content_scroll()
        return scroll

    def _populate_dpi_page(self):
        self._dpi_group = Adw.PreferencesGroup()
        self._dpi_group.set_title("Resolution stages")
        self._dpi_group.set_description("Changes are applied immediately to the device.")
        self._dpi_clamp.set_child(self._dpi_group)

        try:
            resolutions = self._mouse.active_profile.resolutions
        except Exception as exc:
            self._show_error(str(exc))
            return

        for res in resolutions:
            try:
                x, _ = res.dpi
                dpi_list = res.dpi_list
            except Exception:
                continue

            is_active = res.is_active
            row = Adw.ActionRow()
            row.set_title("Active stage" if is_active else "Stage")
            row.set_subtitle(f"{x} DPI")
            if is_active:
                row.add_css_class("accent")

            if dpi_list:
                model = Gtk.StringList()
                closest_idx = 0
                for i, val in enumerate(dpi_list):
                    model.append(str(val))
                    if abs(val - x) < abs(dpi_list[closest_idx] - x):
                        closest_idx = i

                dropdown = Gtk.DropDown(model=model, selected=closest_idx)
                dropdown.set_valign(Gtk.Align.CENTER)

                def on_dpi_changed(dd, _param, r=res, dl=dpi_list, row=row):
                    chosen = dl[dd.get_selected()]
                    r.dpi = chosen
                    row.set_subtitle(f"{chosen} DPI")
                    try:
                        self._mouse.commit()
                    except Exception as e:
                        self._show_error(str(e))

                dropdown.connect("notify::selected", on_dpi_changed)
                row.add_suffix(dropdown)
                row.set_activatable_widget(dropdown)

            self._dpi_group.add(row)

    # ------------------------------------------------------------------
    # Buttons page
    # ------------------------------------------------------------------

    def _build_buttons_page(self):
        scroll, clamp = self._make_content_scroll()

        group = Adw.PreferencesGroup()
        group.set_title("Button mapping")
        group.set_description("Button remapping will be available in a future update.")

        placeholder = Adw.StatusPage()
        placeholder.set_icon_name("input-gaming-symbolic")
        placeholder.set_title("Coming soon")
        placeholder.set_description("Button remapping requires key-capture support.")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.append(group)
        box.append(placeholder)
        clamp.set_child(box)
        return scroll

    # ------------------------------------------------------------------
    # Polling Rate page
    # ------------------------------------------------------------------

    def _build_polling_page(self):
        scroll, self._polling_clamp = self._make_content_scroll()
        return scroll

    def _populate_polling_page(self):
        group = Adw.PreferencesGroup()
        group.set_title("Report rate")
        group.set_description("How many times per second the mouse sends position updates.")
        self._polling_clamp.set_child(group)

        try:
            current = self._mouse.report_rate
            rate_list = self._mouse.report_rate_list
        except Exception as exc:
            self._show_error(str(exc))
            return

        row = Adw.ActionRow()
        row.set_title("Polling rate")
        row.set_subtitle(f"{current} Hz")

        model = Gtk.StringList()
        selected_idx = 0
        for i, hz in enumerate(rate_list):
            model.append(f"{hz} Hz")
            if hz == current:
                selected_idx = i

        dropdown = Gtk.DropDown(model=model, selected=selected_idx)
        dropdown.set_valign(Gtk.Align.CENTER)

        def on_rate_changed(dd, _param):
            chosen = rate_list[dd.get_selected()]
            self._mouse.report_rate = chosen
            row.set_subtitle(f"{chosen} Hz")
            try:
                self._mouse.commit()
            except Exception as e:
                self._show_error(str(e))

        dropdown.connect("notify::selected", on_rate_changed)
        row.add_suffix(dropdown)
        row.set_activatable_widget(dropdown)
        group.add(row)

    # ------------------------------------------------------------------
    # Profiles page
    # ------------------------------------------------------------------

    def _build_profiles_page(self):
        scroll, self._profiles_clamp = self._make_content_scroll()
        return scroll

    def _populate_profiles_page(self):
        group = Adw.PreferencesGroup()
        group.set_title("Profiles")
        group.set_description("Select the active profile on the device.")
        self._profiles_clamp.set_child(group)

        try:
            profiles = self._mouse.profiles
        except Exception as exc:
            self._show_error(str(exc))
            return

        for profile in profiles:
            row = Adw.ActionRow()
            row.set_title(f"Profile {profile.index + 1}")
            row.set_subtitle("Active" if profile.is_active else "")

            check = Gtk.CheckButton()
            check.set_valign(Gtk.Align.CENTER)
            check.set_active(profile.is_active)

            # Group all checkbuttons together so only one can be active
            if profile.index == 0:
                self._profile_check_group = check
            else:
                check.set_group(self._profile_check_group)

            def on_profile_toggled(btn, p=profile, r=row):
                if not btn.get_active():
                    return
                try:
                    self._mouse.set_active_profile(p.index)
                    self._mouse.commit()
                except Exception as e:
                    self._show_error(str(e))
                    return
                # Refresh subtitles
                self._populate_profiles_page()

            check.connect("toggled", on_profile_toggled)
            row.add_prefix(check)
            row.set_activatable_widget(check)
            group.add(row)

    # ------------------------------------------------------------------
    # Sidebar navigation
    # ------------------------------------------------------------------

    def _on_nav_row_selected(self, listbox, row):
        if row is None:
            return
        idx = row.get_index()
        _, title, stack_name = PAGES[idx]
        self._content_page.set_title(title)
        self._split_view.set_show_content(True)

        if self._mouse is None:
            return

        self._content_stack.set_visible_child_name(stack_name)

    # ------------------------------------------------------------------
    # Device loading
    # ------------------------------------------------------------------

    def _load_devices(self):
        try:
            devices = list_devices()
        except Exception as exc:
            self._show_error(str(exc))
            return

        if not devices:
            return

        self._mouse = devices[0]
        self._device_label.set_label(self._mouse.name)

        self._populate_dpi_page()
        self._populate_polling_page()
        self._populate_profiles_page()
        self._content_stack.set_visible_child_name("dpi")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _show_error(self, message):
        dialog = Adw.AlertDialog(heading="Error", body=message)
        dialog.add_response("ok", "OK")
        dialog.present(self)


class LogiTuneApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        win = MainWindow(application=app)
        win.present()


def main():
    app = LogiTuneApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
