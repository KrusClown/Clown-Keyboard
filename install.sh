#!/usr/bin/env bash
# vkbd install script
set -e

echo "==> Installing vkbd dependencies..."
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-evdev

echo "==> Granting /dev/uinput access to your user..."
sudo usermod -aG input "$USER"
# Also set permissions immediately for this session
sudo chmod 660 /dev/uinput 2>/dev/null || true
sudo chgrp input /dev/uinput 2>/dev/null || true

INSTALL_DIR="$HOME/.local/share/vkbd"
echo "==> Installing to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
cp vkbd.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/vkbd.py"

# CLI launcher
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/vkbd" << EOF
#!/usr/bin/env bash
python3 "$INSTALL_DIR/vkbd.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/vkbd"

# .desktop entry
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/vkbd.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=vkbd
GenericName=Virtual Keyboard
Comment=Native GTK3 floating virtual keyboard for Wayland and X11
Exec=$HOME/.local/bin/vkbd
Icon=input-keyboard
Categories=Utility;Accessibility;
Keywords=keyboard;virtual;input;wayland;
StartupNotify=false
EOF

echo ""
echo "✓ vkbd installed!"
echo ""
echo "  IMPORTANT: Log out and back in for the 'input' group to take effect."
echo "  Or run once with sudo:  sudo python3 vkbd.py"
echo ""
echo "  Usage:"
echo "    vkbd                    # dark theme, English"
echo "    vkbd --theme light"
echo "    vkbd --theme contrast   # WCAG AAA high contrast"
echo "    vkbd --lang ES          # Spanish layout"
echo "    vkbd --scale 1.3        # bigger keys"
echo ""
