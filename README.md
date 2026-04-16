# logi-tune-gtk

A lightweight Linux desktop app for configuring Logitech mice on Fedora and other GNOME-based distros. Built with GTK4 and libadwaita — feels native, stays small, and follows your system theme including dark mode.

Talks to `ratbagd` (the `libratbag` daemon) over D-Bus — supports a wide range of Logitech devices without root permissions.

![screenshot placeholder](docs/screenshot.png)

---

## Features

- View and change DPI stages per profile
- Native GNOME look and feel (GTK4 + libadwaita)
- Dark mode support via system theme
- No root required

---

## Requirements

- Fedora 38+ or any GNOME-based distro with GTK4
- Python 3.11+
- `ratbagd` running

---

## Installation

### 1. Install system dependencies

```bash
sudo dnf install python3 python3-gobject gtk4 libadwaita libratbag ratbagd
```

### 2. Start ratbagd

```bash
sudo systemctl enable --now ratbagd
```

### 3. Clone and run

```bash
git clone https://github.com/bladetheblade12/logi-tune-gtk.git
cd logi-tune-gtk
python3 main.py
```

> No virtualenv needed — all dependencies are system packages.

---

## Device not showing up?

- Make sure your mouse is plugged in (USB or receiver)
- Add yourself to the `input` group and re-login:

  ```bash
  sudo usermod -aG input $USER
  ```

- Check if your device is supported: [libratbag/data/devices](https://github.com/libratbag/libratbag/tree/main/data/devices)

---

## Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

---

## License

[MIT](LICENSE)
