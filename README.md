# 🎨 WallPicker

A beautiful radial wallpaper picker for Linux with GTK4, designed for Hyprland and other Wayland compositors.

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/353ffeb2-a7a5-409b-b483-18af9c79bd73" />

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)

## ✨ Features

- 🎯 **Radial Interface** - Unique circular design for wallpaper selection
- 🖼️ **Live Preview** - Hover over wallpapers to see fullscreen preview
- 📄 **Pagination** - Navigate through multiple pages of wallpapers
- ⚡ **Async Loading** - Fast multi-threaded image loading
- 🎨 **Transparent Background** - Clean, modern interface
- ⌨️ **Keyboard Navigation** - Full keyboard support for navigation
- 🔄 **SWWW Integration** - Smooth wallpaper transitions with swww

## 📸 Screenshots

<!-- Add your screenshots here -->

## 🚀 Installation

### Dependencies

Make sure you have the following installed:

```bash
# On Arch Linux
sudo pacman -S python gtk4 python-gobject swww

# On Ubuntu/Debian
sudo apt install python3 libgtk-4-1 python3-gi gir1.2-gtk-4.0
# For swww, install from: https://github.com/LGFae/swww
```

### Quick Install

1. Clone the repository:
```bash
git clone https://github.com/your-username/wallpicker.git
cd wallpicker
```

2. Make the script executable:
```bash
chmod +x wallpicker.py
```

3. (Optional) Create a symlink to use it system-wide:
```bash
sudo ln -s $(pwd)/wallpicker.py /usr/local/bin/wallpicker
```

## 🎮 Usage

### Basic Usage

Set your wallpaper directory (default is `~/.wallpapers`):
```bash
export WALL_DIR="$HOME/.wallpapers"
```

Run the picker:
```bash
python wallpicker.py
# or if you created symlink:
wallpicker
```

### Keyboard Controls

- **ESC** - Close the picker or cancel preview
- **Left Arrow** - Previous page
- **Right Arrow / Space** - Next page
- **Click** - Select wallpaper

### Mouse Controls

- **Hover** - Preview wallpaper after 1.5 seconds
- **Click on sector** - Set wallpaper immediately
- **Click outside circle** - Close picker
- **Click X button** - Close preview

## ⚙️ Configuration

You can customize the picker by editing the constants at the top of `wallpicker.py`:

```python
WALL_DIR = Path(os.environ.get("WALL_DIR", str(Path.home() / ".wallpapers")))
SIZE = 990                  # Window size
INNER_HOLE_RATIO = 0.25     # Size of center hole (0-1)
BG_ALPHA = 0.55             # Background transparency (0-1)
```

### Environment Variables

- `WALL_DIR` - Directory containing your wallpapers (default: `~/.wallpapers`)

## 🔧 Hyprland Integration

Add to your `~/.config/hypr/hyprland.conf`:

```conf
# Wallpaper picker keybind
bind = $mainMod, W, exec, python /path/to/wallpicker.py

# Or with custom wallpaper directory
bind = $mainMod, W, exec, WALL_DIR=$HOME/Pictures/Wallpapers python /path/to/wallpicker.py
```

## 📋 Supported Image Formats

- `.jpg` / `.jpeg`
- `.png`
- `.webp`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [GTK4](https://www.gtk.org/) and [PyGObject](https://pygobject.readthedocs.io/)
- Wallpaper switching powered by [swww](https://github.com/LGFae/swww)
- Inspired by the Hyprland community

## 🐛 Known Issues

- Requires swww daemon to be running
- Best experience on Wayland compositors

## 📮 Contact

Created by [@Huan](https://github.com/your-username)

---

⭐ Star this repository if you find it useful!
