"""
mouse.py — D-Bus interface to ratbagd (libratbag daemon).

Provides a thin Python wrapper around the ratbagd D-Bus API so the rest of
the app never has to speak raw D-Bus directly.
"""

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib
import dbus


RATBAG_BUS_NAME   = "org.freedesktop.ratbag1"
RATBAG_OBJECT     = "/org/freedesktop/ratbag1"
RATBAG_IFACE      = "org.freedesktop.ratbag1.Manager"
DEVICE_IFACE      = "org.freedesktop.ratbag1.Device"
PROFILE_IFACE     = "org.freedesktop.ratbag1.Profile"
RESOLUTION_IFACE  = "org.freedesktop.ratbag1.Resolution"
BUTTON_IFACE      = "org.freedesktop.ratbag1.Button"


def _props(bus, obj_path, iface):
    """Return a dbus.Interface for org.freedesktop.DBus.Properties on obj_path."""
    obj = bus.get_object(RATBAG_BUS_NAME, obj_path)
    return dbus.Interface(obj, "org.freedesktop.DBus.Properties"), obj


class Resolution:
    def __init__(self, bus, path):
        self._props, self._obj = _props(bus, path, RESOLUTION_IFACE)
        self.path = path

    def _get(self, prop):
        return self._props.Get(RESOLUTION_IFACE, prop)

    def _set(self, prop, value):
        self._props.Set(RESOLUTION_IFACE, prop, value)

    @property
    def dpi(self):
        return tuple(self._get("Resolution"))  # (x, y)

    @dpi.setter
    def dpi(self, value):
        """value: (x, y) tuple or single int (applied to both axes)."""
        if isinstance(value, int):
            value = (value, value)
        self._set("Resolution", dbus.Struct(
            [dbus.UInt32(value[0]), dbus.UInt32(value[1])],
            signature="uu"
        ))

    @property
    def is_active(self):
        return bool(self._get("IsActive"))

    @property
    def dpi_list(self):
        """Returns the list of supported DPI values."""
        return list(self._get("ResolutionList"))


class Profile:
    def __init__(self, bus, path):
        self._bus = bus
        self._props, self._obj = _props(bus, path, PROFILE_IFACE)
        self.path = path

    def _get(self, prop):
        return self._props.Get(PROFILE_IFACE, prop)

    @property
    def index(self):
        return int(self._get("Index"))

    @property
    def is_active(self):
        return bool(self._get("IsActive"))

    def set_active(self):
        iface = dbus.Interface(self._obj, PROFILE_IFACE)
        iface.SetActive()

    @property
    def resolutions(self):
        paths = self._get("Resolutions")
        return [Resolution(self._bus, str(p)) for p in paths]

    def commit(self):
        iface = dbus.Interface(self._obj, PROFILE_IFACE)
        iface.Commit()


class Mouse:
    """Represents a single ratbagd-managed device."""

    def __init__(self, bus, path):
        self._bus = bus
        self._props, self._obj = _props(bus, path, DEVICE_IFACE)
        self.path = path

    def _get(self, prop):
        return self._props.Get(DEVICE_IFACE, prop)

    @property
    def name(self):
        return str(self._get("Name"))

    @property
    def model(self):
        return str(self._get("Model"))

    @property
    def profiles(self):
        paths = self._get("Profiles")
        return [Profile(self._bus, str(p)) for p in paths]

    @property
    def active_profile(self):
        for p in self.profiles:
            if p.is_active:
                return p
        return self.profiles[0]

    def commit(self):
        """Persist all pending changes to the device."""
        iface = dbus.Interface(self._obj, DEVICE_IFACE)
        iface.Commit()


def list_devices():
    """Return a list of Mouse objects for every device ratbagd currently sees."""
    bus = dbus.SystemBus()
    manager_obj = bus.get_object(RATBAG_BUS_NAME, RATBAG_OBJECT)
    manager_props = dbus.Interface(manager_obj, "org.freedesktop.DBus.Properties")
    device_paths = manager_props.Get(RATBAG_IFACE, "Devices")
    return [Mouse(bus, str(p)) for p in device_paths]
