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


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Logi Tune")
        self.set_default_size(480, 560)

        self._build_ui()
        self._load_devices()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Root layout
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        # Main content area
        self._stack = Adw.ViewStack()
        toolbar_view.set_content(self._stack)

        # "No device" placeholder page
        status = Adw.StatusPage()
        status.set_icon_name("input-mouse-symbolic")
        status.set_title("No mouse detected")
        status.set_description(
            "Make sure ratbagd is running and your mouse is connected."
        )
        self._stack.add_named(status, "no-device")

        # Device page (populated in _load_devices)
        self._device_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._device_box.set_margin_top(24)
        self._device_box.set_margin_bottom(24)
        self._device_box.set_margin_start(24)
        self._device_box.set_margin_end(24)

        scroll = Gtk.ScrolledWindow()
        scroll.set_child(self._device_box)
        scroll.set_vexpand(True)
        self._stack.add_named(scroll, "device")

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
            self._stack.set_visible_child_name("no-device")
            return

        # Use the first device found
        mouse = devices[0]
        self._populate_device(mouse)
        self._stack.set_visible_child_name("device")

    def _populate_device(self, mouse):
        # Device name banner
        banner = Adw.Banner()
        banner.set_title(mouse.name)
        banner.set_revealed(True)
        self._device_box.append(banner)

        # Active profile
        try:
            profile = mouse.active_profile
            resolutions = profile.resolutions
        except Exception as exc:
            self._show_error(str(exc))
            return

        if not resolutions:
            return

        # DPI group
        dpi_group = Adw.PreferencesGroup()
        dpi_group.set_title("DPI")
        self._device_box.append(dpi_group)

        for res in resolutions:
            try:
                x, y = res.dpi
                dpi_list = res.dpi_list
            except Exception:
                continue

            row = Adw.ActionRow()
            row.set_title(f"{'Active' if res.is_active else 'Stage'} — {x} DPI")
            row.set_subtitle(f"x={x}  y={y}")

            if dpi_list:
                # Dropdown to pick a DPI value
                model = Gtk.StringList()
                closest_idx = 0
                for i, val in enumerate(dpi_list):
                    model.append(str(val))
                    if abs(val - x) < abs(dpi_list[closest_idx] - x):
                        closest_idx = i

                dropdown = Gtk.DropDown(model=model, selected=closest_idx)
                dropdown.set_valign(Gtk.Align.CENTER)

                # Capture res in closure
                def on_dpi_changed(dd, _param, r=res, dl=dpi_list):
                    chosen = dl[dd.get_selected()]
                    r.dpi = chosen
                    try:
                        mouse.commit()
                    except Exception as e:
                        self._show_error(str(e))

                dropdown.connect("notify::selected", on_dpi_changed)
                row.add_suffix(dropdown)

            dpi_group.add(row)

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
