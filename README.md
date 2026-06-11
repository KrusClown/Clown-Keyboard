# Clown-Keyboard
ClownKeyboard is a next-generation virtual keyboard designed specifically for Linux environments. Built with a hybrid Electron + Python architecture, it provides a responsive, accessible, and highly customizable typing experience across both Wayland and X11 display servers.

# Technologies Used
<p align="center">
  <img src="https://skillicons.dev/icons?i=linux&perline=6" />
</p>


# Structure
```text
clownkeyboard/
│
├── frontend/
│   ├── electron/
│   ├── themes/
│   ├── layouts/
│   └── localization/
│
├── backend/
│   ├── wayland/
│   ├── x11/
│   ├── tray/
│   ├── login/
│   └── services/
│
├── plugins/
│
├── docs/
│
├── scripts/
│   ├── install.sh
│   └── package.sh
│
├── packaging/
│   ├── deb/
│   ├── rpm/
│   └── arch/
└── README.md
```

# Installation

| Distribution | Command |
|-------------|----------|
| 🟢 Ubuntu / Debian | `sudo apt install clownkeyboard` |
| 🔵 Fedora | `sudo dnf install clownkeyboard` |
| 🟣 Arch Linux | `sudo pacman -S clownkeyboard` |
| 🟠 openSUSE | `sudo zypper install clownkeyboard` |
| ⚫ Alpine Linux | `sudo apk add clownkeyboard` |
| 🍓 Raspberry Pi OS | `sudo apt install clownkeyboard` |
