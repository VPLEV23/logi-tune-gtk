"""
mouse.py — D-Bus interface to ratbagd (libratbag daemon).

Provides a thin Python wrapper around the ratbagd D-Bus API so the rest of
the app never has to speak raw D-Bus directly.

Set LOGI_MOCK=1 in the environment to use fake data for UI development:
    LOGI_MOCK=1 python3 main.py
"""

import os
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


# ---------------------------------------------------------------------------
# Mock layer — active when LOGI_MOCK=1
# ---------------------------------------------------------------------------

DPI_LIST = [200, 400, 800, 1200, 1600, 2400, 3200, 6400]

class MockResolution:
    def __init__(self, dpi, active):
        self._dpi = dpi
        self.is_active = active
        self.dpi_list = DPI_LIST

    @property
    def dpi(self):
        return (self._dpi, self._dpi)

    @dpi.setter
    def dpi(self, value):
        self._dpi = value if isinstance(value, int) else value[0]


class MockProfile:
    def __init__(self, index, active):
        self.index = index
        self.is_active = active
        self.resolutions = [
            MockResolution(800,  active),
            MockResolution(1600, False),
            MockResolution(3200, False),
        ]

    def set_active(self):
        pass

    def commit(self):
        pass


class MockMouse:
    name = "Logitech G502 HERO (mock)"
    model = "mock-device"
    report_rate = 500
    report_rate_list = [125, 250, 500, 1000]

    def __init__(self):
        self._profiles = [
            MockProfile(0, active=True),
            MockProfile(1, active=False),
            MockProfile(2, active=False),
        ]

    @property
    def profiles(self):
        return self._profiles

    @property
    def active_profile(self):
        return next(p for p in self._profiles if p.is_active)

    def set_active_profile(self, index):
        for p in self._profiles:
            p.is_active = p.index == index

    def commit(self):
        pass


# ---------------------------------------------------------------------------
# Real D-Bus layer
# ---------------------------------------------------------------------------

def _props(bus, obj_path, iface):
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
        dbus.Interface(self._obj, PROFILE_IFACE).SetActive()

    @property
    def resolutions(self):
        paths = self._get("Resolutions")
        return [Resolution(self._bus, str(p)) for p in paths]

    def commit(self):
        dbus.Interface(self._obj, PROFILE_IFACE).Commit()


class Mouse:
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
        dbus.Interface(self._obj, DEVICE_IFACE).Commit()


def list_devices():
    """Return a list of Mouse objects for every device ratbagd currently sees.

    If LOGI_MOCK=1 is set, returns a single MockMouse instead of talking to
    ratbagd — useful for UI development without a physical device.
    """
    if os.environ.get("LOGI_MOCK") == "1":
        return [MockMouse()]

    bus = dbus.SystemBus()
    manager_obj = bus.get_object(RATBAG_BUS_NAME, RATBAG_OBJECT)
    manager_props = dbus.Interface(manager_obj, "org.freedesktop.DBus.Properties")
    device_paths = manager_props.Get(RATBAG_IFACE, "Devices")
    return [Mouse(bus, str(p)) for p in device_paths]
