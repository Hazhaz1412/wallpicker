
import os, math, subprocess, sys, threading, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, cairo, GLib

provider = Gtk.CssProvider()
provider.load_from_data(b"""
window, .background { background-color: transparent; }
""")
Gtk.StyleContext.add_provider_for_display(
    Gdk.Display.get_default(),
    provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)



WALL_DIR = Path(os.environ.get("WALL_DIR", str(Path.home() / ".wallpapers")))
SIZE = 990   
INNER_HOLE_RATIO = 0.25   
BG_ALPHA = 0.55             


def list_images(folder: Path):
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    return sorted([p for p in folder.glob("**/*") if p.suffix.lower() in exts and p.is_file()])

def ensure_swww():
    try:
        subprocess.run(["pgrep", "-x", "swww-daemon"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        subprocess.Popen(["swww-daemon", "--format", "xrgb"])

def load_single_image(path, canvas_size):
    """Load ảnh và scale để cover toàn bộ canvas"""
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file(str(path))
        
        sx = canvas_size / pb.get_width()
        sy = canvas_size / pb.get_height()
        s = max(sx, sy)  
        neww = max(1, int(pb.get_width() * s))
        newh = max(1, int(pb.get_height() * s))
        pb = pb.scale_simple(neww, newh, GdkPixbuf.InterpType.BILINEAR)
        return pb
    except Exception as e:
        print(f"[wallpicker] skip {path}: {e}", file=sys.stderr)
        return None


class RadialPicker(Gtk.ApplicationWindow):
    def __init__(self, app, images):
        super().__init__(application=app, title="wallpicker")
        self.set_default_size(SIZE, SIZE)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        self.images = images
        self.all_images = images 
        self.page_size = 6  
        self.current_page = 0
        self.total_pages = max(1, math.ceil(len(images) / self.page_size))
        
        
        self.current_images = self.get_current_page_images()
        self.n = len(self.current_images)
        self.hovered_sector = -1  
        
        
        self.hover_timer_id = None
        self.hover_start_time = 0
        self.preview_active = False  
        self.preview_pixbuf = None   
        self.preview_image_path = None 
        self.close_button_rect = None  
        
        print(f"[wallpicker] Page {self.current_page + 1}/{self.total_pages} ({len(self.current_images)} images)")

        
        self.canvas_size = SIZE

        self.pixbufs = [None] * self.page_size  
        self.load_cache = {}  
        self.loaded_count = 0
        
        
        self.setup_ui()
        
                
        self.load_images_async(self.current_images, SIZE)

    def get_current_page_images(self):
        """Lấy danh sách ảnh cho trang hiện tại"""
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        return self.all_images[start_idx:end_idx]
    
    def next_page(self):
        """Chuyển sang trang tiếp theo"""
        if self.current_page < self.total_pages - 1:
            self.cancel_hover_timer()
            self.preview_active = False
            self.preview_pixbuf = None
            self.preview_image_path = None
            self.close_button_rect = None
            self.current_page += 1
            self.current_images = self.get_current_page_images()
            self.n = len(self.current_images)
            self.hovered_sector = -1
            self.pixbufs = [None] * self.page_size  
            self.loaded_count = 0
            self.load_images_async(self.current_images, SIZE)
            print(f"[wallpicker] Page {self.current_page + 1}/{self.total_pages}")
            self.area.queue_draw()
    
    def prev_page(self):
        """Chuyển sang trang trước"""
        if self.current_page > 0:
            self.cancel_hover_timer()
            self.preview_active = False
            self.preview_pixbuf = None
            self.preview_image_path = None
            self.close_button_rect = None
            self.current_page -= 1
            self.current_images = self.get_current_page_images()
            self.n = len(self.current_images)
            self.hovered_sector = -1
            self.pixbufs = [None] * self.page_size  
            self.loaded_count = 0
            self.load_images_async(self.current_images, SIZE)
            print(f"[wallpicker] Page {self.current_page + 1}/{self.total_pages}")
            self.area.queue_draw()

    def load_images_async(self, images, target_size):
        """Load ảnh trong background thread"""
        print(f"[wallpicker] Loading {len(images)} images in background...", flush=True)
        
        def load_worker():
            with ThreadPoolExecutor(max_workers=4) as executor:
                
                future_to_index = {
                    executor.submit(load_single_image, path, target_size): i 
                    for i, path in enumerate(images)
                }
                
                
                for future in as_completed(future_to_index):
                    index = future_to_index[future]
                    result = future.result()
                    
                    
                    GLib.idle_add(self.on_image_loaded, index, result)
        
        
        threading.Thread(target=load_worker, daemon=True).start()
    
    def on_image_loaded(self, index, pixbuf):
        """Callback khi một ảnh được load xong"""
        if index < len(self.pixbufs): 
            self.pixbufs[index] = pixbuf
            self.loaded_count += 1
            
            
            if self.loaded_count % 3 == 0 or self.loaded_count == len(self.current_images):
                print(f"[wallpicker] Loaded {self.loaded_count}/{len(self.current_images)} images")
            
            
            if hasattr(self, 'area') and (self.loaded_count % 2 == 0 or self.loaded_count == len(self.current_images)):
                self.area.queue_draw()
        return False 

    def start_hover_timer(self, sector_idx):
        """Bắt đầu timer cho hover preview"""
        if self.hover_timer_id:
            GLib.source_remove(self.hover_timer_id)
        
        def on_hover_timeout():
            if (self.hovered_sector == sector_idx and 
                sector_idx < len(self.current_images) and 
                not self.preview_active):
                
                
                preview_path = self.current_images[sector_idx]
                self.preview_pixbuf = load_single_image(preview_path, SIZE)
                
                if self.preview_pixbuf:
                    self.preview_active = True
                    self.preview_image_path = str(preview_path)
                    print(f"[wallpicker] Canvas preview: {preview_path}")
                    
                    
                    self.area.grab_focus()
                    
                   
                    self.area.queue_draw()
            
            self.hover_timer_id = None
            return False  
        
        
        self.hover_timer_id = GLib.timeout_add(1500, on_hover_timeout)

    def cancel_hover_timer(self):
        """Hủy hover timer"""
        if self.hover_timer_id:
            GLib.source_remove(self.hover_timer_id)
            self.hover_timer_id = None

    def setup_ui(self):
        """Setup UI elements"""
        
        self.area = Gtk.DrawingArea()
        self.area.set_content_width(SIZE)
        self.area.set_content_height(SIZE)
        self.area.set_draw_func(self.on_draw)
        self.set_child(self.area)

        
        click = Gtk.GestureClick()
        click.connect("released", self.on_released)
        self.area.add_controller(click)

        
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self.on_motion)
        motion.connect("leave", self.on_leave)
        self.area.add_controller(motion)

        
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self.on_key_pressed)
        self.area.add_controller(key)
        
        
        self.area.set_can_focus(True)
        self.area.grab_focus()

    def on_draw(self, area, cr: cairo.Context, width, height):
        
        cr.save()
        cr.set_operator(cairo.Operator.CLEAR)
        cr.paint()
        cr.restore()
        cr.set_operator(cairo.Operator.OVER)

        
        if hasattr(cairo, "Antialias"):
            cr.set_antialias(cairo.Antialias.BEST)

        cx, cy = width/2, height/2
        radius = min(width, height)/2
        inner = radius * INNER_HOLE_RATIO

        
        cr.new_path()
        cr.set_source_rgba(0, 0, 0, BG_ALPHA)
        cr.arc(cx, cy, radius, 0, 2*math.pi)
        cr.fill()

        
        for i in range(self.n):
            a1 = 2*math.pi*i/self.n
            a2 = 2*math.pi*(i+1)/self.n

            
            cr.new_path()
            cr.move_to(cx + inner*math.cos(a1), cy + inner*math.sin(a1))
            cr.arc(cx, cy, radius, a1, a2)
            cr.line_to(cx + inner*math.cos(a2), cy + inner*math.sin(a2))
            cr.arc_negative(cx, cy, inner, a2, a1)
            cr.close_path()

            cr.save()
            cr.clip()

            pb = self.pixbufs[i]
            if pb is not None:
                
                mid_angle = (a1 + a2) / 2
                
                
                
                angle_width = a2 - a1
                
                
                
                points = []
                
                points.append((cx + inner * math.cos(a1), cy + inner * math.sin(a1)))
                points.append((cx + inner * math.cos(a2), cy + inner * math.sin(a2)))
                
                points.append((cx + radius * math.cos(a1), cy + radius * math.sin(a1)))
                points.append((cx + radius * math.cos(a2), cy + radius * math.sin(a2)))
                
                
                for j in range(1, 4):
                    angle = a1 + j * angle_width / 4
                    points.append((cx + inner * math.cos(angle), cy + inner * math.sin(angle)))
                    points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
                
                
                min_x = min(p[0] for p in points)
                max_x = max(p[0] for p in points)
                min_y = min(p[1] for p in points)
                max_y = max(p[1] for p in points)
                
                sector_width = max_x - min_x
                sector_height = max_y - min_y
                
                
                scale_x = sector_width / pb.get_width()
                scale_y = sector_height / pb.get_height()
                scale = max(scale_x, scale_y) * 1.1  
                
                
                sector_center_x = (min_x + max_x) / 2
                sector_center_y = (min_y + max_y) / 2
                
                
                cr.save()
                cr.translate(sector_center_x, sector_center_y)
                cr.scale(scale, scale)
                cr.translate(-pb.get_width() / 2, -pb.get_height() / 2)
                Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
                cr.paint()
                cr.restore()
            else:
                
                cr.set_source_rgb(0.2, 0.2, 0.2)
                cr.paint()
                
                
                if i < len(self.current_images):
                    cr.set_source_rgba(1, 1, 1, 0.8)
                    cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.NORMAL)
                    cr.set_font_size(14)
                    
                    mid_angle = (a1 + a2) / 2
                    mid_radius = (radius + inner) / 2
                    text_x = cx + mid_radius * math.cos(mid_angle)
                    text_y = cy + mid_radius * math.sin(mid_angle)
                    
                    loading_text = "..."
                    text_extents = cr.text_extents(loading_text)
                    cr.move_to(text_x - text_extents.width/2, text_y + text_extents.height/2)
                    cr.show_text(loading_text)

            cr.restore()

            
            cr.set_source_rgba(1, 1, 1, 0.18)
            cr.set_line_width(2.0)
            cr.move_to(cx + inner*math.cos(a1), cy + inner*math.sin(a1))
            cr.line_to(cx + radius*math.cos(a1), cy + radius*math.sin(a1))
            cr.stroke()

        
        cr.set_source_rgba(1, 1, 1, 0.18)
        cr.set_line_width(2.0)
        cr.arc(cx, cy, radius, 0, 2*math.pi)
        cr.stroke()
        if INNER_HOLE_RATIO > 0:
            cr.arc(cx, cy, inner, 0, 2*math.pi)
            cr.stroke()

        
        if self.hovered_sector >= 0 and self.hovered_sector < self.n:
            i = self.hovered_sector
            a1 = 2*math.pi*i/self.n
            a2 = 2*math.pi*(i+1)/self.n
            
            
            cr.new_path()
            cr.move_to(cx + inner*math.cos(a1), cy + inner*math.sin(a1))
            cr.arc(cx, cy, radius, a1, a2)
            cr.line_to(cx + inner*math.cos(a2), cy + inner*math.sin(a2))
            cr.arc_negative(cx, cy, inner, a2, a1)
            cr.close_path()
            
            
            cr.set_source_rgba(1, 1, 1, 0.25)
            cr.fill_preserve()
            
            
            cr.set_source_rgba(1, 1, 1, 0.8)
            cr.set_line_width(4.0)
            cr.stroke()

        
        if self.preview_active and self.preview_pixbuf:
            
            cr.set_source_rgba(0, 0, 0, 0.8)
            cr.rectangle(0, 0, width, height)
            cr.fill()
            
            
            preview_w = self.preview_pixbuf.get_width()
            preview_h = self.preview_pixbuf.get_height()
            
            
            canvas_margin = 50
            available_w = width - 2 * canvas_margin
            available_h = height - 2 * canvas_margin
            
            scale_x = available_w / preview_w
            scale_y = available_h / preview_h
            scale = min(scale_x, scale_y)
            
            final_w = preview_w * scale
            final_h = preview_h * scale
            
            preview_x = (width - final_w) / 2
            preview_y = (height - final_h) / 2
            
            cr.save()
            cr.translate(preview_x, preview_y)
            cr.scale(scale, scale)
            Gdk.cairo_set_source_pixbuf(cr, self.preview_pixbuf, 0, 0)
            cr.paint()
            cr.restore()
            
            
            cr.set_source_rgba(1, 1, 1, 0.8)
            cr.set_line_width(3.0)
            cr.rectangle(preview_x, preview_y, final_w, final_h)
            cr.stroke()
            
            
            close_button_size = 40
            close_x = preview_x + final_w - close_button_size
            close_y = preview_y
            
            
            cr.set_source_rgba(0, 0, 0, 0.8)
            cr.rectangle(close_x, close_y, close_button_size, close_button_size)
            cr.fill()
            
            
            cr.set_source_rgba(1, 1, 1, 0.8)
            cr.set_line_width(2.0)
            cr.rectangle(close_x, close_y, close_button_size, close_button_size)
            cr.stroke()
            
            
            cr.set_source_rgba(1, 1, 1, 1.0)
            cr.set_line_width(3.0)
            
            cr.move_to(close_x + 10, close_y + 10)
            cr.line_to(close_x + close_button_size - 10, close_y + close_button_size - 10)
            cr.stroke()
            
            cr.move_to(close_x + close_button_size - 10, close_y + 10)
            cr.line_to(close_x + 10, close_y + close_button_size - 10)
            cr.stroke()
            
            
            self.close_button_rect = (close_x, close_y, close_button_size, close_button_size)
            
            
            if self.preview_image_path:
                filename = os.path.basename(self.preview_image_path)
                cr.set_source_rgba(1, 1, 1, 1.0)
                cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
                cr.set_font_size(16)
                
                text_extents = cr.text_extents(filename)
                text_x = (width - text_extents.width) / 2
                text_y = preview_y - 10
                
                
                cr.set_source_rgba(0, 0, 0, 0.7)
                padding = 8
                cr.rectangle(text_x - padding, text_y - text_extents.height - padding,
                           text_extents.width + 2*padding, text_extents.height + 2*padding)
                cr.fill()
                
                cr.set_source_rgba(1, 1, 1, 1.0)
                cr.move_to(text_x, text_y)
                cr.show_text(filename)
                
            
            cr.set_source_rgba(1, 1, 1, 0.9)
            cr.set_font_size(14)
            instruction = "Click to set wallpaper • ESC to cancel"
            text_extents = cr.text_extents(instruction)
            text_x = (width - text_extents.width) / 2
            text_y = preview_y + final_h + 30
            
            cr.move_to(text_x, text_y)
            cr.show_text(instruction)
            
            
            return

        
        if self.total_pages > 1:
            cr.set_source_rgba(1, 1, 1, 0.9)
            cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
            cr.set_font_size(18)
            
            page_text = f"{self.current_page + 1}/{self.total_pages}"
            text_extents = cr.text_extents(page_text)
            text_x = cx - text_extents.width / 2
            text_y = cy + text_extents.height / 2
            
            
            cr.set_source_rgba(0, 0, 0, 0.8)
            padding = 10
            cr.rectangle(text_x - padding, text_y - text_extents.height - padding, 
                        text_extents.width + 2*padding, text_extents.height + 2*padding)
            cr.fill()
            
            
            cr.set_source_rgba(1, 1, 1, 1.0)
            cr.move_to(text_x, text_y)
            cr.show_text(page_text)
            
            
            cr.set_font_size(24)
            
            
            if self.current_page > 0:
                cr.set_source_rgba(1, 1, 1, 0.9)
                cr.move_to(cx - 60, cy + 10)
                cr.show_text("<")
            
            
            if self.current_page < self.total_pages - 1:
                cr.set_source_rgba(1, 1, 1, 0.9)
                cr.move_to(cx + 40, cy + 10)
                cr.show_text(">")
            
            
            cr.set_font_size(10)
            nav_text = ""
            nav_extents = cr.text_extents(nav_text)
            nav_x = cx - nav_extents.width / 2
            nav_y = cy + 35
            
            cr.set_source_rgba(1, 1, 1, 0.7)
            cr.move_to(nav_x, nav_y)
            cr.show_text(nav_text)

        
        if self.preview_active:
            cr.set_source_rgba(1, 0.2, 0.2, 0.9)  
            cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
            cr.set_font_size(16)
            
            preview_text = "PREVIEW - Click to close"
            text_extents = cr.text_extents(preview_text)
            text_x = cx - text_extents.width / 2
            text_y = cy - 50  
            
            
            cr.set_source_rgba(0, 0, 0, 0.9)
            padding = 12
            cr.rectangle(text_x - padding, text_y - text_extents.height - padding, 
                        text_extents.width + 2*padding, text_extents.height + 2*padding)
            cr.fill()
            
            
            cr.set_source_rgba(1, 0.2, 0.2, 1.0)
            cr.move_to(text_x, text_y)
            cr.show_text(preview_text)

    def on_key_pressed(self, controller, keyval, keycode, state):
        """Xử lý keyboard input"""
        if keyval == Gdk.KEY_Escape:
            if self.preview_active:
                
                self.preview_active = False
                self.preview_pixbuf = None
                self.preview_image_path = None
                self.close_button_rect = None
                self.area.queue_draw()
                return True
            else:
                
                self.destroy()
                return True
        elif keyval == Gdk.KEY_Right or keyval == Gdk.KEY_space:
            if not self.preview_active:  
                self.next_page()
                return True
        elif keyval == Gdk.KEY_Left:
            if not self.preview_active:  
                self.prev_page()
                return True
        return False

    def on_released(self, gesture, n_press, x, y):
        width = self.area.get_allocated_width()
        height = self.area.get_allocated_height()
        cx, cy = width/2, height/2
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        radius = min(width, height)/2
        inner = radius * INNER_HOLE_RATIO

        
        if self.preview_active:
            
            if self.close_button_rect:
                close_x, close_y, close_w, close_h = self.close_button_rect
                if (close_x <= x <= close_x + close_w and 
                    close_y <= y <= close_y + close_h):
                    
                    self.preview_active = False
                    self.preview_pixbuf = None
                    self.preview_image_path = None
                    self.close_button_rect = None
                    self.area.queue_draw()
                    print("[wallpicker] Preview closed via X button")
                    return
            
            
            if self.preview_image_path:
                wp = str(self.preview_image_path)
                ensure_swww()
                subprocess.run([
                    "swww", "img", wp,
                    "--transition-type", "any",
                    "--transition-fps", "60",
                    "--transition-duration", "0.6"
                ])
                print(f"[wallpicker] Set wallpaper: {wp}")
            self.destroy()
            return

        
        if self.total_pages > 1:
            
            if (dx >= -90 and dx <= -40 and abs(dy) < 30 and self.current_page > 0):
                print(f"[DEBUG] Clicked left arrow")
                self.prev_page()
                return
            
            elif (dx >= 30 and dx <= 80 and abs(dy) < 30 and self.current_page < self.total_pages - 1):
                print(f"[DEBUG] Clicked right arrow")
                self.next_page()
                return

        
        if r < inner or r > radius:
            self.destroy()
            return

        
        angle = math.atan2(dy, dx) % (2*math.pi)
        idx = int(angle / (2*math.pi) * self.n)
        if idx < len(self.current_images):
            wp = str(self.current_images[idx])

            ensure_swww()
            subprocess.run([
                "swww", "img", wp,
                "--transition-type", "any",
                "--transition-fps", "60",
                "--transition-duration", "0.6"
            ])
            self.destroy()

    def get_sector_at_position(self, x, y):
        """Trả về index của sector tại vị trí (x, y), hoặc -1 nếu không trong sector nào"""
        width = self.area.get_allocated_width()
        height = self.area.get_allocated_height()
        cx, cy = width/2, height/2
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        radius = min(width, height)/2
        inner = radius * INNER_HOLE_RATIO

        if r < inner or r > radius:
            return -1

        angle = math.atan2(dy, dx) % (2*math.pi)
        idx = int(angle / (2*math.pi) * self.n)
        return idx

    def on_motion(self, controller, x, y):
        """Xử lý mouse motion để highlight sector và bắt đầu hover timer"""
        new_sector = self.get_sector_at_position(x, y)
        if new_sector != self.hovered_sector:
            
            self.cancel_hover_timer()
            
            self.hovered_sector = new_sector
            self.area.queue_draw()  
            
            
            if new_sector >= 0 and new_sector < len(self.current_images):
                self.start_hover_timer(new_sector)

    def on_leave(self, controller):
        """Xử lý khi mouse leave khỏi widget"""
        self.cancel_hover_timer()
        if self.hovered_sector != -1:
            self.hovered_sector = -1
            self.area.queue_draw()
        
        
        
        
        
        
        


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="dev.huan.wallpicker")

    def do_activate(self):
        if not WALL_DIR.exists():
            print(f"[wallpicker] Folder not found: {WALL_DIR}", file=sys.stderr); sys.exit(1)
        images = list_images(WALL_DIR)
        if not images:
            print(f"[wallpicker] No images in {WALL_DIR}", file=sys.stderr); sys.exit(1)
        win = RadialPicker(self, images)
        win.present()

def main():
    app = App()
    app.run()

if __name__ == "__main__":
    main()
