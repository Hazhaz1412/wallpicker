#!/bin/bash

# Installation script for WallPicker

echo "🎨 Installing WallPicker..."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check for GTK4
if ! python3 -c "import gi; gi.require_version('Gtk', '4.0')" 2>/dev/null; then
    echo "❌ GTK4 is not installed."
    echo "Please install it:"
    echo "  Arch: sudo pacman -S gtk4 python-gobject"
    echo "  Ubuntu/Debian: sudo apt install libgtk-4-1 python3-gi gir1.2-gtk-4.0"
    exit 1
fi

# Check for swww
if ! command -v swww &> /dev/null; then
    echo "⚠️  Warning: swww is not installed."
    echo "WallPicker requires swww for wallpaper switching."
    echo "Install from: https://github.com/LGFae/swww"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Make wallpicker.py executable
chmod +x wallpicker.py
echo "✅ Made wallpicker.py executable"

# Create symlink
INSTALL_PATH="/usr/local/bin/wallpicker"
if [ -w "/usr/local/bin" ]; then
    ln -sf "$(pwd)/wallpicker.py" "$INSTALL_PATH"
    echo "✅ Created symlink at $INSTALL_PATH"
else
    echo "⚠️  No write permission for /usr/local/bin"
    echo "Run with sudo to create system-wide symlink:"
    echo "  sudo ln -s $(pwd)/wallpicker.py $INSTALL_PATH"
fi

# Create default wallpaper directory
WALL_DIR="$HOME/.wallpapers"
if [ ! -d "$WALL_DIR" ]; then
    mkdir -p "$WALL_DIR"
    echo "✅ Created wallpaper directory at $WALL_DIR"
else
    echo "ℹ️  Wallpaper directory already exists at $WALL_DIR"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Usage:"
echo "  wallpicker                    # Use default wallpaper directory"
echo "  WALL_DIR=~/Pictures wallpicker # Use custom directory"
echo ""
echo "Add to Hyprland config:"
echo "  bind = \$mainMod, W, exec, wallpicker"
