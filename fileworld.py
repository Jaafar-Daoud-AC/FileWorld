from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.prefabs.input_field import InputField
from pathlib import Path
import json
import math
import random
import shutil
import time as pytime
import colorsys
from PIL import Image, ImageDraw, ImageChops, ImageOps
from panda3d.core import TransparencyAttrib, SamplerState
from panda3d.core import Texture as PTexture

# نظام ملفات ثلاثي الابعاد (نسخة MVP)
# كل ملف او مجلد يظهر كمجسم عائم، داخل مجلد واحد فقط خاص بالبرنامج

app = Ursina(title="Cube OS")

BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR / "CubeOS_Root"          # المجلد الوحيد الذي يراه البرنامج
LAYOUT_FILE = ROOT / ".layout.json"      # يحفظ اماكن المجسمات
current = ROOT                           # المجلد المفتوح حاليا

TEXT_EXT = {".txt", ".md", ".py", ".json", ".csv", ".log", ".ini", ".cfg",
            ".html", ".css", ".js"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico"}
MAX_EDIT_SIZE = 20000                    # اكبر حجم ملف نصي يمكن تعديله (بايت)
FLOAT_Y = 1.8                            # ارتفاع المجسمات عن الارض
SPRINT_MULT = 2.2                        # سرعة الجري (اضغط Shift اثناء المشي)
TURBO_MULT = 5.0                         # وضع التسريع الدائم (مفتاح T)

# الايقونة (تتجاهل اذا كان مسار المشروع فيه حروف عربية لان ويندوز لا يقرأها)
if (BASE_DIR / "minecraft.ico").exists() and str(BASE_DIR).isascii():
    window.icon = "minecraft.ico"


# ---------- صور الخلفية والارضية (تُنشأ تلقائيا اذا لم تكن موجودة) ----------
# --- ASSETS START ---
ASSETS_DIR = BASE_DIR / "assets"
SKY_FILE = "cubeos_sky.png"        # يمكنك استبدالها بصورة خلفية حاسوبك
FLOOR_FILE = "cubeos_floor.png"
GLOW_FILE = "cubeos_glow.png"      # نقطة مضيئة ناعمة (للشهب والنجوم والسراريب)
PLANET_FILE = "cubeos_planet.png"  # سطح الكوكب
RING_FILE = "cubeos_ring.png"      # حلقة الكوكب
SKY_REPEAT = 1                     # اجعلها 4 اذا كانت صورتك غير بانورامية (تتكرر 4 مرات)


def make_sky(path):
    w, h = 2048, 1024
    img = Image.new("RGB", (w, h), (1, 1, 8))
    # سدم ملونة (العمود الاخير = الاول حتى لا يظهر خط في الالتفاف)
    for cols, rows, power in ((8, 4, 1.0), (24, 12, 0.5)):
        small = Image.new("RGB", (cols + 1, rows + 1))
        px = small.load()
        for y in range(rows + 1):
            for x in range(cols):
                px[x, y] = (int(random.randint(0, 45) * power),
                            int(random.randint(0, 20) * power),
                            int(random.randint(5, 90) * power))
            px[cols, y] = px[0, y]
        img = ImageChops.add(img, small.resize((w, h), Image.BICUBIC))
    # نجوم
    d = ImageDraw.Draw(img)
    for _ in range(2200):
        x, y, b = random.randrange(w), random.randrange(h), random.randint(110, 255)
        d.point((x, y), fill=(b, b, b))
    for _ in range(160):
        x, y = random.randrange(w), random.randrange(h)
        r, tint = random.choice((1, 1, 2)), random.choice(((255, 255, 255), (180, 200, 255), (255, 220, 170)))
        d.ellipse([x - r, y - r, x + r, y + r], fill=tint)
    for _ in range(30):
        x, y = random.randrange(w), random.randrange(h)
        d.line([x - 6, y, x + 6, y], fill=(150, 160, 200))
        d.line([x, y - 6, x, y + 6], fill=(150, 160, 200))
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 255, 255))
    img.save(path)


def draw_digit(d, x, y, ch, col):
    w, h = 26, 38
    if ch == "0":
        d.ellipse([x, y, x + w, y + h], outline=col, width=4)
    else:
        d.line([x + w // 2, y, x + w // 2, y + h], fill=col, width=4)
        d.line([x + w // 2, y, x + 4, y + 10], fill=col, width=4)
        d.line([x + 4, y + h, x + w - 4, y + h], fill=col, width=4)


def make_floor(path):
    size, cell = 512, 64
    bg = (0, 10, 0)
    img = Image.new("RGB", (size, size), bg)
    d = ImageDraw.Draw(img)
    # اصفار وواحدات
    for cy in range(size // cell):
        for cx in range(size // cell):
            if random.random() < 0.6:
                g = random.randint(70, 190)
                draw_digit(d, cx * cell + 19, cy * cell + 13,
                           random.choice("01"), (0, g, 0))
    # اسلاك خضراء مع عقد
    for _ in range(9):
        gx, gy = random.randrange(1, 8), random.randrange(1, 8)
        pts = [(gx * cell, gy * cell)]
        for _ in range(random.randint(2, 4)):
            dx, dy = random.choice(((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1)))
            n = random.randint(1, 3)
            gx = max(0, min(8, gx + dx * n))
            gy = max(0, min(8, gy + dy * n))
            pts.append((gx * cell, gy * cell))
        pts = [(min(p[0], size - 1), min(p[1], size - 1)) for p in pts]
        d.line(pts, fill=(0, 190, 60), width=5)
        for p in (pts[0], pts[-1]):
            d.ellipse([p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9], fill=bg,
                      outline=(0, 255, 90), width=4)
    d.rectangle([0, 0, size - 1, size - 1], outline=(0, 70, 0), width=2)
    img.save(path)


def make_glow(path):
    s = 128
    img = Image.new("RGBA", (s, s))
    px = img.load()
    for y in range(s):
        for x in range(s):
            d = math.hypot(x - s / 2 + 0.5, y - s / 2 + 0.5) / (s / 2)
            a = max(0.0, 1.0 - d)
            px[x, y] = (255, 255, 255, int(255 * a ** 2.2))
    img.save(path)


def make_planet(path):
    w, h = 512, 256
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        v = y / h
        band = 0.5 + 0.5 * math.sin(v * 38 + 3 * math.sin(v * 7))
        c = (int(150 + 90 * band), int(95 + 80 * band), int(60 + 70 * band))
        d.line([0, y, w, y], fill=c)
    for _ in range(14):                       # عواصف صغيرة
        x, y = random.randrange(w), random.randrange(20, h - 20)
        rw, rh = random.randint(10, 40), random.randint(4, 10)
        d.ellipse([x - rw, y - rh, x + rw, y + rh], fill=(230, 190, 150))
    img = img.filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(1.5))
    img.save(path)


def make_ring(path):
    s = 512
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s // 2
    for r in range(int(c * 0.52), c - 1):
        u = (r - c * 0.52) / (c * 0.48)
        if 0.52 < u < 0.60:                   # فجوة بين الحلقات
            continue
        a = int(70 + 130 * abs(math.sin(u * 23)) * (1 - 0.5 * u))
        d.ellipse([c - r, c - r, c + r, c + r], outline=(225, 205, 170, a), width=2)
    img.save(path)


def ensure_assets():
    ASSETS_DIR.mkdir(exist_ok=True)
    for name, fn in ((SKY_FILE, make_sky), (FLOOR_FILE, make_floor), (GLOW_FILE, make_glow),
                     (PLANET_FILE, make_planet), (RING_FILE, make_ring)):
        try:
            if not (ASSETS_DIR / name).exists():
                fn(ASSETS_DIR / name)
        except Exception:
            pass
# --- ASSETS END ---


# ---------- تجهيز المجلد الاولي ----------
def setup_root():
    if ROOT.exists():
        return
    (ROOT / "Documents").mkdir(parents=True)
    (ROOT / "Pictures").mkdir()
    (ROOT / "Projects").mkdir()
    (ROOT / "readme.txt").write_text(
        "Welcome to Cube OS.\n\nDouble click an object to open it.\n"
        "Right click for options.", encoding="utf-8")
    (ROOT / "notes.txt").write_text("My first note.", encoding="utf-8")
    (ROOT / "Documents" / "todo.txt").write_text(
        "- learn python\n- build projects\n- publish on github", encoding="utf-8")
    (ROOT / "Projects" / "hello.py").write_text(
        "print('hello world')", encoding="utf-8")


# التأكد ان المسار داخل المجلد الخاص فقط
def is_safe(path):
    p = Path(path).resolve()
    return p == ROOT.resolve() or ROOT.resolve() in p.parents


# اسم صالح (بدون مسارات)
def valid_name(name):
    bad = ("/", "\\", ":", "*", "?", '"', "<", ">", "|")
    return bool(name) and not name.startswith(".") and not any(c in name for c in bad)


# ---------- حفظ اماكن المجسمات ----------
layout = {}


def load_layout():
    global layout
    try:
        layout = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))
    except Exception:
        layout = {}


def save_layout():
    try:
        LAYOUT_FILE.write_text(json.dumps(layout), encoding="utf-8")
    except Exception:
        pass


def folder_key(folder):
    return Path(folder).relative_to(ROOT).as_posix()


def slot_pos(i):
    return ((i % 5 - 2) * 3.5, (i // 5) * 3.5)


def free_slot(used):
    i = 0
    while True:
        x, z = slot_pos(i)
        if not any(abs(ux - x) < 2.5 and abs(uz - z) < 2.5 for ux, uz in used):
            return (x, z)
        i += 1


# ---------- المجسمات (كل نوع ملف له شكل) ----------
def icon_kind(path, kind):
    if kind in ("dir", "up"):
        return kind
    ext = path.suffix.lower()
    if ext == ".py":
        return "py"
    if ext in (".txt", ".md", ".log", ".csv", ".json"):
        return "txt"
    if ext in IMAGE_EXT:
        return "img"
    return "file"


def build_icon(pivot, k):
    def part(model, pos, scale, col, rot=(0, 0, 0)):
        Entity(parent=pivot, model=model, position=pos, scale=scale,
               color=col, rotation=rot)

    if k == "dir":            # مجلد
        part("cube", (0, 0.02, 0), (0.9, 0.62, 0.2), color.orange)
        part("cube", (-0.26, 0.37, 0), (0.38, 0.12, 0.2), color.orange)
        part("cube", (0, -0.08, -0.13), (0.9, 0.5, 0.08), color.yellow)
        part("cube", (0, -0.08, 0.13), (0.9, 0.5, 0.08), color.yellow)
    elif k == "up":           # سهم للرجوع
        part("cube", (0, 0, 0), (0.95, 0.95, 0.06), color.orange)
        part("cube", (0, -0.2, 0), (0.26, 0.45, 0.2), color.white)
        part("cube", (0, 0.15, 0), (0.4, 0.4, 0.2), color.white, (0, 0, 45))
    elif k == "txt":          # ملف نصي
        part("cube", (0, 0, 0), (0.7, 0.92, 0.08), color.white)
        for i in range(4):
            for zz in (-0.05, 0.05):
                part("cube", (0, 0.2 - i * 0.14, zz), (0.46, 0.05, 0.04), color.gray)
    elif k == "py":           # ملف بايثون
        part("cube", (0, 0, 0), (0.7, 0.92, 0.08), color.azure)
        part("cube", (0, 0.2, 0), (0.7, 0.2, 0.1), color.yellow)
        part("cube", (0, -0.2, 0), (0.4, 0.2, 0.1), color.white)
    elif k == "img":          # صورة
        part("cube", (0, 0, 0), (0.9, 0.7, 0.08), color.dark_gray)
        part("cube", (0, 0, 0), (0.76, 0.56, 0.1), color.cyan)
        part("sphere", (0.2, 0.1, 0), (0.2, 0.2, 0.2), color.yellow)
        part("cube", (-0.12, -0.1, 0), (0.26, 0.26, 0.14), color.green, (0, 0, 45))
        part("cube", (0.1, -0.14, 0), (0.2, 0.2, 0.14), color.lime, (0, 0, 45))
    else:                     # اي ملف اخر
        part("cube", (0, 0, 0), (0.7, 0.92, 0.08), color.light_gray)
        part("cube", (0, 0.1, 0), (0.4, 0.06, 0.1), color.gray)
        part("cube", (0, -0.1, 0), (0.4, 0.06, 0.1), color.gray)


# --- IMAGES START ---
# ---------- الصور: تحميل (من الذاكرة، بدون مشاكل المسارات العربية) ----------
THUMB_SIDE = 256                         # دقة الصورة المصغرة العائمة
VIEW_SIDE = 2048                         # اقصى دقة عند فتح الصورة
FLIP_TB = getattr(Image, "Transpose", Image).FLIP_TOP_BOTTOM
tex_cache = {}                           # (المسار, تاريخ التعديل, الدقة) -> نتيجة


def load_image_tex(path, max_side):
    """يرجع (texture, (w, h), (الاصلي_w, الاصلي_h)) او None اذا تعذر قراءة الصورة"""
    try:
        key = (str(path), path.stat().st_mtime, max_side)
    except OSError:
        return None
    if key in tex_cache:
        return tex_cache[key]
    try:
        im = Image.open(path)
        orig = im.size
        try:
            im.draft("RGB", (max_side, max_side))   # يسرع صور JPEG الكبيرة
        except Exception:
            pass
        try:
            im = ImageOps.exif_transpose(im)        # اتجاه صور الهاتف الصحيح
        except Exception:
            pass
        im = im.convert("RGBA")
        im.thumbnail((max_side, max_side), Image.LANCZOS)
        w, h = im.size
        tex = PTexture(path.name)
        tex.setup2dTexture(w, h, PTexture.T_unsigned_byte, PTexture.F_rgba)
        tex.setRamImageAs(im.transpose(FLIP_TB).tobytes(), "RGBA")
        tex.setMinfilter(SamplerState.FT_linear)
        tex.setMagfilter(SamplerState.FT_linear)
        tex.setWrapU(SamplerState.WM_clamp)
        tex.setWrapV(SamplerState.WM_clamp)
    except Exception:
        return None
    if len(tex_cache) > 120:
        tex_cache.pop(next(iter(tex_cache)))
    tex_cache[key] = (tex, (w, h), orig)
    return tex_cache[key]


def textured_quad(parent, tex, **kw):
    q = Entity(parent=parent, model="quad", color=color.white, **kw)
    q.model.setTexture(tex, 1)
    q.setTransparency(TransparencyAttrib.M_alpha)
    return q


def build_image_icon(pivot, path):
    """صورة حقيقية عائمة داخل اطار، تظهر من الوجهين"""
    res = load_image_tex(path, THUMB_SIDE)
    if not res:
        return False
    tex, (w, h), _ = res
    ar = w / h
    qw, qh = (1.2, 1.2 / ar) if ar >= 1 else (1.2 * ar, 1.2)
    Entity(parent=pivot, model="cube", scale=(qw + 0.1, qh + 0.1, 0.07), color=color.dark_gray)
    for z, ry in ((-0.045, 0), (0.045, 180)):
        q = textured_quad(pivot, tex, position=(0, 0, z), scale=(qw, qh), rotation_y=ry)
        q.setLightOff()
    return True
# --- IMAGES END ---


# ---------- العنصر (ملف او مجلد) ----------
class Item(Button):
    def __init__(self, path, kind, position):
        super().__init__(
            parent=scene,
            position=position,
            model="cube",        # صندوق غير مرئي للنقر عليه
            scale=2.2,
            color=color.white,
        )
        self.visible_self = False
        self.path = path
        self.kind = kind
        self.phase = (hash(path.name) % 100) / 10
        self._last = pytime.time()
        self.target = None       # وجهة الانزلاق عند اعادة الترتيب

        # المجسم الذي يدور ويطفو
        self.pivot = Entity(parent=self)
        shape = icon_kind(path, kind)
        self.is_img = False
        if shape == "img":
            try:
                self.is_img = build_image_icon(self.pivot, path)
            except Exception:
                import traceback
                traceback.print_exc()
                for c in list(self.pivot.children):      # تنظيف ما بُني جزئيا
                    destroy(c)
        if not self.is_img:
            build_icon(self.pivot, shape)

        # الظل على الارض والاسم
        self.shadow = Entity(model="quad", rotation_x=90, scale=(1.8, 1.8),
                             color=color.black66)
        name = ".." if kind == "up" else path.name
        if len(name) > 16:
            name = name[:14] + ".."
        self.label = Text(text=name, parent=scene, billboard=True,
                          scale=10, origin=(0, 0))
        self.place(position[0], position[2])

    def place(self, x, z):
        self.position = Vec3(x, FLOAT_Y, z)
        self.label.position = Vec3(x, 0.4, z)
        self.shadow.position = Vec3(x, 0.03, z)

    def glide_to(self, x, z):
        self.target = (x, z)

    def update(self):
        now = pytime.time()
        dt = min(now - self._last, 0.1)
        self._last = now
        if self.target:                      # انزلاق ناعم الى المكان الجديد
            tx, tz = self.target
            k = min(1.0, 7 * dt)
            nx, nz = self.x + (tx - self.x) * k, self.z + (tz - self.z) * k
            if abs(nx - tx) < 0.03 and abs(nz - tz) < 0.03:
                nx, nz, self.target = tx, tz, None
            self.place(nx, nz)
        if self.is_img:                      # الصورة تتمايل ببطء لتبقى واضحة
            self.pivot.rotation_y = math.sin(now * 0.8 + self.phase) * 35
        else:
            self.pivot.rotation_y += 25 * dt
        self.pivot.y = math.sin(now * 2 + self.phase) * 0.04
        self.pivot.scale = 1.2 if self.hovered else 1


world = []        # كل عناصر المشهد الحالي
floor = None
hud = None
message = None
carry = {"item": None, "orig": None, "dist": 5.0}   # العنصر الذي نحمله


def clear_world():
    for e in world:
        destroy(e.label)
        destroy(e.shadow)
        destroy(e)
    world.clear()
    carry["item"] = None


def build_world():
    clear_world()
    entries = sorted((p for p in current.iterdir() if not p.name.startswith(".")),
                     key=lambda p: (p.is_file(), p.name.lower()))

    # الاماكن المحفوظة (والجديد ياخذ مكانا فارغا)
    data = layout.setdefault(folder_key(current), {})
    names = {p.name for p in entries}
    for old in [n for n in data if n not in names]:
        del data[old]
    used = [tuple(v) for v in data.values()]
    for p in entries:
        if p.name not in data:
            pos = free_slot(used)
            data[p.name] = list(pos)
            used.append(pos)
    save_layout()

    failed = 0
    if current != ROOT:
        world.append(Item(current.parent, "up", (-10.5, FLOAT_Y, 0)))
    for p in entries:
        x, z = data[p.name]
        try:
            world.append(Item(p, "dir" if p.is_dir() else "file", (x, FLOAT_Y, z)))
        except Exception:
            import traceback
            traceback.print_exc()
            failed += 1
    if failed:
        notify("%d item(s) failed to load (see console)" % failed)

    player.position = (0, 1, -6)
    hud.text = "/" + str(current.relative_to(ROOT.parent)).replace("\\", "/")


def notify(text):
    message.text = text
    invoke(setattr, message, "text", "", delay=3)


# ---------- واجهة (قوائم ونوافذ) ----------
ui = None
viewer = {"ent": None, "path": None, "base": (1, 1), "zoom": 1.0,
          "info": None, "orig": (0, 0), "last": None}


def open_ui():
    global ui
    close_ui()
    player.enabled = False
    mouse.locked = False
    ui = Entity(parent=camera.ui)
    return ui


def close_ui():
    global ui
    if ui:
        destroy(ui)
        ui = None
    viewer["ent"] = None
    player.enabled = True
    mouse.locked = True


def show_menu(options):
    panel = open_ui()
    Entity(parent=panel, model="quad", color=color.black66,
           scale=(0.34, 0.06 * len(options) + 0.04), z=1)
    top = 0.03 * len(options)
    for i, (label, func) in enumerate(options):
        b = Button(parent=panel, text=label, scale=(0.3, 0.05),
                   y=top - 0.03 - i * 0.06)
        b.on_click = lambda f=func: (close_ui(), f())


def ask_name(title, callback, default=""):
    panel = open_ui()
    Entity(parent=panel, model="quad", color=color.black66, scale=(0.6, 0.22), z=1)
    Text(parent=panel, text=title, origin=(0, 0), y=0.07)
    field = InputField(parent=panel, default_value=default, active=True,
                       character_limit=40, y=0.015)

    def submit():
        name = field.text.strip()
        close_ui()
        if name:
            callback(name)

    ok = Button(parent=panel, text="OK", scale=(0.18, 0.045), x=-0.11, y=-0.06)
    ok.on_click = submit
    cancel = Button(parent=panel, text="Cancel", scale=(0.18, 0.045), x=0.11, y=-0.06)
    cancel.on_click = close_ui


# محرر النصوص: اكتب ثم اضغط Save
def edit_file(path):
    ext = path.suffix.lower()
    if ext not in TEXT_EXT:
        return notify("This file type can't be opened")
    if path.stat().st_size > MAX_EDIT_SIZE:
        return notify("File is too large to edit")
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return notify("Cannot read this file")

    panel = open_ui()
    Entity(parent=panel, model="quad", color=color.black90, scale=(0.85, 0.8), z=1)
    Text(parent=panel, text=path.name, origin=(0, 0), y=0.35, color=color.yellow)
    field = InputField(parent=panel, default_value=content, max_lines=10,
                       character_limit=MAX_EDIT_SIZE, active=True, y=0.03)

    def save():
        try:
            path.write_text(field.text, encoding="utf-8")
            notify("Saved: " + path.name)
        except Exception:
            notify("Could not save")

    Button(parent=panel, text="Save", scale=(0.18, 0.05), x=-0.11, y=-0.35, on_click=save)
    Button(parent=panel, text="Close", scale=(0.18, 0.05), x=0.11, y=-0.35, on_click=close_ui)


# عارض الصور: تكبير بالعجلة، سحب بالفأرة، الاسهم للتنقل
def image_files(folder):
    try:
        return sorted((p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")
                       and p.suffix.lower() in IMAGE_EXT), key=lambda p: p.name.lower())
    except OSError:
        return []


def viewer_refresh():
    v = viewer
    if not v["ent"]:
        return
    bw, bh = v["base"]
    v["ent"].scale = (bw * v["zoom"], bh * v["zoom"])
    files = image_files(v["path"].parent)
    idx = files.index(v["path"]) + 1 if v["path"] in files else 1
    v["info"].text = "%s   %dx%d   (%d/%d)   %d%%" % (
        v["path"].name, v["orig"][0], v["orig"][1], idx, max(1, len(files)), round(v["zoom"] * 100))


def viewer_zoom(factor):
    viewer["zoom"] = max(0.25, min(10.0, viewer["zoom"] * factor))
    viewer_refresh()


def viewer_fit():
    viewer["zoom"] = 1.0
    if viewer["ent"]:
        viewer["ent"].x = viewer["ent"].y = 0
    viewer_refresh()


def viewer_step(d):
    files = image_files(viewer["path"].parent)
    if len(files) < 2 or viewer["path"] not in files:
        return
    view_image(files[(files.index(viewer["path"]) + d) % len(files)])


def viewer_input(key):
    if key in ("scroll up", "+", "=", "numpad +"):
        viewer_zoom(1.2)
    elif key in ("scroll down", "-", "numpad -"):
        viewer_zoom(1 / 1.2)
    elif key == "right arrow":
        viewer_step(1)
    elif key == "left arrow":
        viewer_step(-1)
    elif key == "r":
        viewer_fit()


def view_image(path):
    res = load_image_tex(path, VIEW_SIDE)
    if not res:
        return notify("Cannot open this image")
    tex, (w, h), orig = res
    panel = open_ui()
    Entity(parent=panel, model="quad", color=color.black90, scale=(4, 2), z=1)
    fit = min(window.aspect_ratio * 0.96 / w, 0.74 / h)
    img = textured_quad(panel, tex, scale=(w * fit, h * fit), z=0.5)
    viewer.update(ent=img, path=path, base=(w * fit, h * fit), zoom=1.0, orig=orig, last=None,
                  info=Text(parent=panel, origin=(0, 0), y=0.44, color=color.yellow, z=-1))
    for i, (label, func) in enumerate((("< Prev", lambda: viewer_step(-1)),
                                       ("Next >", lambda: viewer_step(1)),
                                       ("Zoom +", lambda: viewer_zoom(1.25)),
                                       ("Zoom -", lambda: viewer_zoom(0.8)),
                                       ("Fit", viewer_fit),
                                       ("Close", close_ui))):
        Button(parent=panel, text=label, scale=(0.13, 0.05), x=-0.35 + i * 0.14, y=-0.44,
               z=-1, on_click=func)
    viewer_refresh()


# ---------- العمليات ----------
def go_to(path):
    global current
    if is_safe(path):
        current = path
        build_world()


def go_up():
    if current != ROOT:
        go_to(current.parent)


def open_item(item):
    if item.kind in ("dir", "up"):
        go_to(item.path)
    elif item.path.suffix.lower() in IMAGE_EXT:
        view_image(item.path)
    else:
        edit_file(item.path)


def new_folder(name):
    target = current / name
    if not valid_name(name) or not is_safe(target) or target.exists():
        return notify("Invalid name or already exists")
    target.mkdir()
    build_world()


def new_file(name):
    if "." not in name:
        name += ".txt"
    target = current / name
    if not valid_name(name) or not is_safe(target) or target.exists():
        return notify("Invalid name or already exists")
    target.write_text("", encoding="utf-8")
    build_world()
    edit_file(target)       # افتحه فورا للكتابة


def rename_item(item):
    def do(name):
        target = item.path.parent / name
        if not valid_name(name) or not is_safe(target) or target.exists():
            return notify("Invalid name or already exists")
        old = item.path.name
        item.path.rename(target)
        data = layout.get(folder_key(current), {})
        if old in data:
            data[name] = data.pop(old)
        build_world()
    ask_name("Rename", do, item.path.name)


def delete_item(item):
    def do():
        if not is_safe(item.path):
            return
        if item.path.is_dir():
            shutil.rmtree(item.path)
        else:
            item.path.unlink()
        layout.get(folder_key(current), {}).pop(item.path.name, None)
        build_world()
    show_menu([("Yes, delete", do), ("Cancel", lambda: None)])


# ---------- حمل العناصر ونقلها ----------
def start_carry(item):
    if item.kind == "up":
        return
    carry["item"] = item
    carry["orig"] = (item.x, item.z)
    carry["dist"] = 5.0
    item.target = None
    item.collider = None      # حتى لا يمنع المؤشر من رؤية ما خلفه
    notify("Click to drop | Scroll: distance | click a folder to move inside | Esc: cancel")


def end_carry():
    item = carry["item"]
    if item:
        item.collider = "box"
    carry["item"] = None


def cancel_carry():
    item = carry["item"]
    if item:
        item.place(*carry["orig"])
    end_carry()


def spot_taken(x, z, ignore):
    return any(e is not ignore and abs(e.x - x) < 2.5 and abs(e.z - z) < 2.5 for e in world)


def move_into(item, folder):
    target = folder / item.path.name
    if not is_safe(target) or target.exists():
        return notify("Cannot move here (name exists)")
    shutil.move(str(item.path), str(target))
    layout.get(folder_key(current), {}).pop(item.path.name, None)
    end_carry()
    build_world()
    notify("Moved")


def drop_item(hovered):
    item = carry["item"]
    # وضعه فوق مجلد = نقله الى داخل المجلد
    if isinstance(hovered, Item) and hovered is not item and hovered.kind in ("dir", "up"):
        return move_into(item, hovered.path)

    x, z = item.x, item.z
    if hovered is floor and mouse.world_point:
        x, z = mouse.world_point.x, mouse.world_point.z
    x, z = round(x * 2) / 2, round(z * 2) / 2
    if spot_taken(x, z, item):
        return notify("This spot is taken")
    item.place(x, z)
    layout.setdefault(folder_key(current), {})[item.path.name] = [x, z]
    save_layout()
    end_carry()


# ---------- ترتيب الملفات والاماكن ----------
ARR = {"sort": "name", "shape": "grid", "reverse": False}
SORTS = ["name", "type", "size", "date"]
SHAPES = ["grid", "circle", "spiral", "columns"]
KIND_ORDER = {"dir": 0, "py": 1, "txt": 2, "img": 3, "file": 4}
X_LIM, Z_MIN, Z_MAX = 37, -15, 57          # حدود الارضية الامنة
CENTER = (0, 16)                           # مركز الدائرة والحلزون


def sort_key(item):
    p, k = item.path, ARR["sort"]
    name = p.name.lower()
    try:
        st = p.stat()
    except OSError:
        return (0, 0, name)
    if k == "type":
        return (KIND_ORDER[icon_kind(p, item.kind)], p.suffix.lower(), name)
    if k == "size":
        size = len(list(p.iterdir())) if p.is_dir() else st.st_size
        return (p.is_file(), size, name)
    if k == "date":
        return (-st.st_mtime, name)
    return (p.is_file(), name)


def shape_positions(items):
    n, shape = len(items), ARR["shape"]
    cx, cz = CENTER
    pos = []
    if shape == "circle":                  # حلقات متداخلة
        k = 0
        while len(pos) < n:
            r = 6 + 4 * k
            cap = max(1, int(2 * math.pi * r / 3.6))
            for j in range(min(cap, n - len(pos))):
                a = 2 * math.pi * j / cap
                pos.append((cx + math.sin(a) * r, cz + math.cos(a) * r))
            k += 1
    elif shape == "spiral":                # حلزون ذهبي
        for i in range(n):
            r, a = 2.1 * math.sqrt(i + 0.6), i * 2.39996
            pos.append((cx + math.sin(a) * r, cz + math.cos(a) * r))
    elif shape == "columns":               # عمود لكل نوع ملف
        groups = {}
        for i, it in enumerate(items):
            groups.setdefault(KIND_ORDER[icon_kind(it.path, it.kind)], []).append(i)
        cols = []
        for key in sorted(groups):
            ids = groups[key]
            for s in range(0, len(ids), 8):
                cols.append(ids[s:s + 8])
        pos = [None] * n
        for ci, col in enumerate(cols):
            x = (ci - (len(cols) - 1) / 2) * 4.5
            for row, i in enumerate(col):
                pos[i] = (x, row * 3.5)
    else:                                  # شبكة
        pos = [slot_pos(i) for i in range(n)]
    return [(max(-X_LIM, min(X_LIM, x)), max(Z_MIN, min(Z_MAX, z))) for x, z in pos]


def apply_arrange(announce=True):
    items = [e for e in world if e.kind != "up"]
    if not items:
        return notify("Nothing to arrange")
    items.sort(key=sort_key, reverse=ARR["reverse"])
    data = layout.setdefault(folder_key(current), {})
    for it, (x, z) in zip(items, shape_positions(items)):
        x, z = round(x * 2) / 2, round(z * 2) / 2
        it.glide_to(x, z)
        data[it.path.name] = [x, z]
    save_layout()
    if announce:
        notify("Arranged: %s / %s%s" % (ARR["sort"], ARR["shape"], " (reversed)" if ARR["reverse"] else ""))


def snap_all():
    G, taken = 3.5, set()
    data = layout.setdefault(folder_key(current), {})
    for it in sorted((e for e in world if e.kind != "up"), key=lambda e: (e.z, e.x)):
        cx, cz = round(it.x / G), round(it.z / G)
        r, found = 0, None
        while not found:
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if max(abs(dx), abs(dz)) == r and (cx + dx, cz + dz) not in taken:
                        found = (cx + dx, cz + dz)
                        break
                if found:
                    break
            r += 1
        taken.add(found)
        x, z = found[0] * G, found[1] * G
        it.glide_to(x, z)
        data[it.path.name] = [x, z]
    save_layout()
    notify("Snapped to grid")


def arrange_menu():
    def cycle(key, values):
        ARR[key] = values[(values.index(ARR[key]) + 1) % len(values)]
        arrange_menu()

    def flip():
        ARR["reverse"] = not ARR["reverse"]
        arrange_menu()

    show_menu([
        ("Sort by: %s  >" % ARR["sort"].title(), lambda: cycle("sort", SORTS)),
        ("Shape: %s  >" % ARR["shape"].title(), lambda: cycle("shape", SHAPES)),
        ("Reverse: %s" % ("On" if ARR["reverse"] else "Off"), flip),
        ("Apply arrangement", apply_arrange),
        ("Snap all to grid", snap_all),
        ("Cancel", lambda: None),
    ])


# حفظ واسترجاع تخطيطات مسماة (3 خانات لكل مجلد)
def presets_here():
    return layout.setdefault("::presets::", {}).setdefault(folder_key(current), {})


def save_preset(slot):
    data = layout.get(folder_key(current), {})
    presets_here()[str(slot)] = {k: list(v) for k, v in data.items()}
    save_layout()
    notify("Layout saved in slot %d" % slot)


def load_preset(slot):
    saved = presets_here().get(str(slot))
    if not saved:
        return notify("Slot %d is empty" % slot)
    data = layout.setdefault(folder_key(current), {})
    for it in world:
        if it.kind != "up" and it.path.name in saved:
            x, z = saved[it.path.name]
            it.glide_to(x, z)
            data[it.path.name] = [x, z]
    save_layout()
    notify("Layout loaded from slot %d" % slot)


def slot_menu(action, title):
    have = presets_here()
    show_menu([("%s slot %d%s" % (title, s, "  (used)" if str(s) in have else ""),
                lambda s=s: action(s)) for s in (1, 2, 3)] + [("Back", layouts_menu)])


def reset_layout():
    ARR.update(sort="name", shape="grid", reverse=False)
    apply_arrange(False)
    notify("Layout reset")


def layouts_menu():
    show_menu([
        ("Save layout  >", lambda: slot_menu(save_preset, "Save to")),
        ("Load layout  >", lambda: slot_menu(load_preset, "Load")),
        ("Reset to default grid", reset_layout),
        ("Cancel", lambda: None),
    ])


# قائمة الزر الايمن على الارض
def folder_menu():
    show_menu([
        ("New Folder", lambda: ask_name("New folder name", new_folder)),
        ("New File", lambda: ask_name("New file name (ex: a.txt)", new_file)),
        ("Arrange items  >", arrange_menu),
        ("Saved layouts  >", layouts_menu),
        ("Sky effects  >", sky_menu),
        ("Refresh", build_world),
        ("Go Up", go_up),
        ("Cancel", lambda: None),
    ])


# قائمة الزر الايمن على عنصر
def item_menu(item):
    if item.kind == "up":
        return folder_menu()
    show_menu([
        ("Open", lambda: open_item(item)),
        ("Pick up (move)", lambda: start_carry(item)),
        ("Rename", lambda: rename_item(item)),
        ("Delete", lambda: delete_item(item)),
        ("Cancel", lambda: None),
    ])


# ---------- المدخلات ----------
last_click = {"item": None, "time": 0}


def input(key):
    if key == "escape":
        if carry["item"]:
            cancel_carry()      # الغاء الحمل
        elif ui:
            close_ui()          # اغلاق النافذة المفتوحة
        else:
            application.quit()  # الخروج من البرنامج
        return
    if ui:
        if viewer["ent"]:
            viewer_input(key)
        return

    hovered = mouse.hovered_entity

    # التسريع ومؤثرات السماء (تعمل حتى اثناء الحمل)
    if key == "t":
        upd["turbo"] = not upd["turbo"]
        notify("Turbo ON (x%g)" % TURBO_MULT if upd["turbo"] else "Turbo OFF")
    if key == "m":
        meteor_shower()
    if key == "c":
        launch_comet()

    # اثناء حمل عنصر
    if carry["item"]:
        if key == "scroll up":
            carry["dist"] = min(30, carry["dist"] + 1)
        if key == "scroll down":
            carry["dist"] = max(2, carry["dist"] - 1)
        if key == "left mouse down":
            drop_item(hovered)
        if key == "right mouse down":
            cancel_carry()
        return

    if key == "left mouse down" and isinstance(hovered, Item):
        now = pytime.time()
        # نقرتين متتاليتين = فتح
        if last_click["item"] is hovered and now - last_click["time"] < 0.4:
            open_item(hovered)
            last_click["item"] = None
        else:
            last_click["item"] = hovered
            last_click["time"] = now

    if key == "right mouse down":
        if isinstance(hovered, Item):
            item_menu(hovered)
        else:
            folder_menu()

    if key == "backspace":
        go_up()
    if key == "g":
        arrange_menu()
    if key == "k":
        sky_menu()


upd = {"last": pytime.time(), "turbo": False, "label": ""}


def update():
    now = pytime.time()
    dt = min(now - upd["last"], 0.1)
    upd["last"] = now

    # سحب الصورة المكبرة في العارض
    if viewer["ent"]:
        cur = (mouse.x, mouse.y)
        if viewer["last"] and held_keys["left mouse"] and not isinstance(mouse.hovered_entity, Button):
            viewer["ent"].x += cur[0] - viewer["last"][0]
            viewer["ent"].y += cur[1] - viewer["last"][1]
        viewer["last"] = cur

    # العنصر المحمول يتبع اللاعب
    item = carry["item"]
    if item:
        p = player.position + player.forward * carry["dist"]
        item.place(p.x, p.z)

    # التسريع: Shift = جري، T = تسريع دائم
    shift = held_keys["left shift"] or held_keys["right shift"] or held_keys["shift"]
    moving = (held_keys["w"] or held_keys["a"] or held_keys["s"] or held_keys["d"]
              or held_keys["up arrow"] or held_keys["down arrow"]
              or held_keys["left arrow"] or held_keys["right arrow"])
    if upd["turbo"]:
        mult, name = TURBO_MULT, "TURBO"
    elif shift:
        mult, name = SPRINT_MULT, "SPRINT"
    else:
        mult, name = 1.0, ""
    player.speed = BASE_SPEED * mult
    label = "%s x%g" % (name, mult) if name else ""
    if label != upd["label"]:
        upd["label"] = label
        speed_text.text = label
    target_fov = BASE_FOV + ((10 if mult <= SPRINT_MULT else 20) if (mult > 1 and moving) else 0)
    camera.fov = lerp(camera.fov, target_fov, min(1.0, 7 * dt))

    # البقاء فوق الارضية (مهم مع السرعة العالية)
    if player.enabled:
        player.x = max(-38.5, min(38.5, player.x))
        player.z = max(-18.5, min(58.5, player.z))
    # اذا سقط اللاعب لاي سبب يرجع الى نقطة البداية
    if player.y < -10:
        player.position = (0, 1, -6)

    sky_fx_update(dt)


# ---------- مؤثرات السماء: شهب ونيازك ومذنب وشفق وكوكب ونجوم متلألئة ----------
SKY_R = 225                                  # نصف قطر السماء (الكرة الخلفية 250)
SKY = {"aurora": True, "meteors": True, "comet": True,
       "twinkle": True, "fireflies": True, "planet": True}
SKY_LABELS = [("aurora", "Aurora"), ("meteors", "Shooting stars"), ("comet", "Comets"),
              ("twinkle", "Twinkling stars"), ("fireflies", "Fireflies"), ("planet", "Planet")]
fx = {"root": None, "t": 0.0, "frame": 0, "meteors": [], "next_meteor": 2.0, "shower": 0.0,
      "comet": None, "next_comet": 20.0, "stars": [], "aurora": [], "planet": None, "flies": []}
glow_tex = None
METEOR_COLORS = [((1.0, 0.97, 0.85), (1.0, 0.5, 0.15)),     # ذهبي
                 ((0.85, 0.93, 1.0), (0.25, 0.5, 1.0)),     # ازرق
                 ((0.8, 1.0, 0.85), (0.1, 0.8, 0.4)),       # اخضر
                 ((1.0, 0.85, 0.95), (0.8, 0.2, 0.8))]      # بنفسجي
STAR_COLORS = [(1, 1, 1), (0.7, 0.8, 1), (1, 0.88, 0.65)]


def dome(az, el, r=1.0):
    return Vec3(r * math.cos(el) * math.sin(az), r * math.sin(el), r * math.cos(el) * math.cos(az))


def glow_quad(parent, pos, size, col):
    e = Entity(parent=parent, model="quad", texture=glow_tex, position=pos,
               scale=size, color=col, billboard=True)
    e.setLightOff()
    e.setTransparency(TransparencyAttrib.M_alpha)
    e.set_depth_write(False)
    return e


class Streak:
    """شهاب او مذنب: نقطة مضيئة تسير على قوس من السماء ويتبعها ذيل متلاشٍ"""

    def __init__(self, root, n, size, speed, life, step, head, tail, fade_in, fade_out, falling=True):
        self.a = dome(random.uniform(0, math.tau), random.uniform(0.3, 1.25))
        r = Vec3(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        b = (r - self.a * r.dot(self.a)).normalized()
        self.b = -b if (falling and b.y > 0) else b      # الشهب تسقط للاسفل
        self.n, self.size, self.speed, self.life, self.step = n, size, speed, life, step
        self.fade_in, self.fade_out, self.age = fade_in, fade_out, 0.0
        self.cols, self.quads = [], []
        for k in range(n):
            f = k / max(1, n - 1)
            c = tuple(head[i] + (tail[i] - head[i]) * f for i in range(3))
            self.cols.append(c)
            self.quads.append(glow_quad(root, Vec3(0, -999, 0), size, Color(*c, 0)))

    def update(self, dt):
        self.age += dt
        if self.age >= self.life:
            return False
        th = self.speed * self.age
        fade = min(1.0, self.age / self.fade_in) * min(1.0, (self.life - self.age) / self.fade_out)
        for k, q in enumerate(self.quads):
            tk = th - k * self.step
            if tk < 0:
                q.color = Color(*self.cols[k], 0)
                continue
            p = (self.a * math.cos(tk) + self.b * math.sin(tk)) * SKY_R
            f = 1 - k / self.n
            horizon = max(0.0, min(1.0, (p.y + 5) / 50))
            q.position = p
            q.scale = self.size * (0.25 + 0.75 * f)
            q.color = Color(*self.cols[k], fade * horizon * f ** 1.4)
        return True

    def destroy(self):
        for q in self.quads:
            destroy(q)


class Aurora:
    """شفق قطبي: ستارة متموجة باربعة صفوف الوان وشفافية (حافة سفلية ناعمة)"""
    N = 44

    def __init__(self, root, center, span, radius, seed, palette):
        self.center, self.span, self.R, self.seed, self.pal = center, span, radius, seed, palette
        n = self.N
        self.tris = []
        for i in range(n):
            for row in (0, 1, 2):
                a, b = i * 4 + row, (i + 1) * 4 + row
                self.tris += [(a, a + 1, b), (a + 1, b + 1, b)]
        self.mesh = Mesh(vertices=[Vec3(0, 0, 0)] * (4 * (n + 1)), triangles=self.tris,
                         colors=[Color(1, 1, 1, 0)] * (4 * (n + 1)), static=False)
        self.ent = Entity(parent=root, model=self.mesh, double_sided=True)
        self.ent.setLightOff()
        self.ent.setTransparency(TransparencyAttrib.M_alpha)
        self.ent.set_depth_write(False)

    def update(self, t, power):
        verts, cols, sd = [], [], self.seed
        for i in range(self.N + 1):
            u = i / self.N
            a = self.center + (u - 0.5) * self.span
            r = self.R + 9 * (0.6 * math.sin(a * 6 + t * 0.5 + sd) + 0.4 * math.sin(a * 13 - t * 0.8))
            yb = 28 + 9 * math.sin(a * 4 + t * 0.35 + sd)
            hgt = 70 + 30 * math.sin(a * 7 - t * 0.6 + sd) + 15 * math.sin(t * 0.2 + sd)
            sx, cz = math.sin(a), math.cos(a)
            for hy, k in ((-0.12, 1.0), (0.0, 1.0), (0.45, 0.97), (1.0, 0.93)):
                verts.append(Vec3(r * k * sx, yb + hgt * hy, r * k * cz))
            edge = math.sin(u * math.pi) ** 0.7
            inten = max(0.0, 0.45 + 0.35 * math.sin(a * 5 + t * 0.9 + sd)
                        + 0.2 * math.sin(a * 28 - t * 1.5)) * edge * power
            inten = min(1.0, inten)
            cols += [Color(*self.pal[0], 0.0), Color(*self.pal[0], 0.6 * inten),
                     Color(*self.pal[1], 0.3 * inten), Color(*self.pal[2], 0.0)]
        self.mesh.vertices = verts
        self.mesh.colors = cols
        self.mesh.generate()


def spawn_meteor():
    head, tail = random.choice(METEOR_COLORS)
    big = random.random() < 0.12             # كرة نارية كبيرة احيانا
    fx["meteors"].append(Streak(
        fx["root"], n=18 if big else 12, size=11 if big else 6,
        speed=random.uniform(0.55, 1.0),
        life=random.uniform(1.0, 1.6) if big else random.uniform(0.6, 1.1),
        step=0.014, head=head, tail=tail, fade_in=0.1, fade_out=0.35))


def spawn_comet():
    fx["comet"] = Streak(fx["root"], n=40, size=20, speed=0.028, life=70, step=0.011,
                         head=(0.85, 0.95, 1.0), tail=(1.0, 0.65, 0.3),
                         fade_in=4, fade_out=8, falling=False)


def meteor_shower():
    fx["shower"] = 8.0
    notify("Meteor shower!")


def launch_comet():
    if fx["comet"]:
        return notify("A comet is already crossing the sky")
    spawn_comet()
    notify("A comet appears...")


def sky_apply():
    for a in fx["aurora"]:
        a.ent.enabled = SKY["aurora"]
    for q, *_ in fx["stars"]:
        q.enabled = SKY["twinkle"]
    for q, *_ in fx["flies"]:
        q.enabled = SKY["fireflies"]
    if fx["planet"]:
        fx["planet"][0].enabled = SKY["planet"]


def sky_menu():
    def flip(k):
        SKY[k] = not SKY[k]
        sky_apply()
        sky_menu()

    show_menu([("%s: %s" % (label, "On" if SKY[k] else "Off"), lambda k=k: flip(k))
               for k, label in SKY_LABELS] +
              [("Meteor shower now", meteor_shower), ("Launch a comet", launch_comet),
               ("Close", lambda: None)])


def sky_fx_init():
    global glow_tex
    glow_tex = load_texture(GLOW_FILE)
    root = fx["root"] = Entity()
    for _ in range(90):                      # نجوم كبيرة متلألئة
        c = random.choice(STAR_COLORS)
        q = glow_quad(root, dome(random.uniform(0, math.tau), random.uniform(0.05, 1.5), SKY_R * 0.98),
                      random.uniform(2, 5), Color(*c, 0.8))
        fx["stars"].append((q, c, random.uniform(0.8, 3.0), random.uniform(0, 6.3)))
    fx["aurora"] = [
        Aurora(root, 0.15, 1.9, 205, 0.0, ((0.2, 1.0, 0.5), (0.1, 0.8, 0.85), (0.55, 0.2, 0.9))),
        Aurora(root, -1.0, 1.4, 215, 3.0, ((0.3, 0.9, 1.0), (0.5, 0.4, 1.0), (0.9, 0.2, 0.8))),
    ]
    p_tex, r_tex = load_texture(PLANET_FILE), load_texture(RING_FILE)
    if p_tex:                                # كوكب بحلقة
        pos = dome(2.4, 0.38, SKY_R * 0.97)
        grp = Entity(parent=root, position=pos)
        tilt = Entity(parent=grp, rotation_z=-18)
        planet = Entity(parent=tilt, model="sphere", scale=24, texture=p_tex)
        planet.setLightOff()
        if r_tex:
            ring = Entity(parent=tilt, model="quad", scale=72, rotation_x=90,
                          texture=r_tex, double_sided=True)
            ring.setLightOff()
            ring.setTransparency(TransparencyAttrib.M_alpha)
        glow_quad(root, pos * 1.02, 62, Color(0.6, 0.75, 1.0, 0.18))
        fx["planet"] = (grp, planet)
    cols = [(0.8, 1.0, 0.3), (0.4, 0.9, 1.0), (1.0, 0.6, 0.9)]
    for _ in range(45):                      # يراعات قرب الارض
        c = random.choice(cols)
        base = Vec3(random.uniform(-36, 36), random.uniform(0.6, 4), random.uniform(-15, 56))
        q = glow_quad(scene, base, random.uniform(0.35, 0.7), Color(*c, 0.8))
        fx["flies"].append((q, c, base, random.uniform(0, 6.3)))
    sky_apply()


def sky_fx_update(dt):
    root = fx["root"]
    if not root:
        return
    fx["t"] += dt
    fx["frame"] += 1
    t, fr = fx["t"], fx["frame"]
    root.position = sky.position = Vec3(player.x, 0, player.z)   # السماء تتبع اللاعب

    # شهب (وزخات)
    fx["shower"] = max(0.0, fx["shower"] - dt)
    if (SKY["meteors"] or fx["shower"] > 0) and len(fx["meteors"]) < 18:
        fx["next_meteor"] -= dt
        if fx["next_meteor"] <= 0:
            spawn_meteor()
            fx["next_meteor"] = random.uniform(0.06, 0.25) if fx["shower"] > 0 else random.uniform(1.5, 5.0)
    alive = []
    for m in fx["meteors"]:
        if m.update(dt):
            alive.append(m)
        else:
            m.destroy()
    fx["meteors"] = alive

    # مذنب
    c = fx["comet"]
    if c:
        if not c.update(dt):
            c.destroy()
            fx["comet"], fx["next_comet"] = None, random.uniform(90, 180)
    elif SKY["comet"]:
        fx["next_comet"] -= dt
        if fx["next_comet"] <= 0:
            spawn_comet()

    # نجوم متلألئة (ثلث العدد في كل اطار)
    if SKY["twinkle"]:
        for q, col, sp, ph in fx["stars"][fr % 3::3]:
            q.color = Color(*col, 0.25 + 0.75 * (0.5 + 0.5 * math.sin(t * sp + ph)))

    # شفق
    if SKY["aurora"] and fr % 2 == 0:
        power = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(t * 0.2))
        for a in fx["aurora"]:
            a.update(t, power)

    # الكوكب
    if SKY["planet"] and fx["planet"]:
        fx["planet"][1].rotation_y += 2 * dt

    # يراعات
    if SKY["fireflies"]:
        for q, col, base, ph in fx["flies"][fr % 3::3]:
            q.position = base + Vec3(math.sin(t * 0.7 + ph) * 1.4, math.sin(t * 1.1 + ph * 2) * 0.6,
                                     math.cos(t * 0.5 + ph) * 1.4)
            q.color = Color(*col, 0.15 + 0.85 * (0.5 + 0.5 * math.sin(t * 2.2 + ph * 3)))


# ---------- بناء العالم ----------
setup_root()
load_layout()

# الفضاء والارضية
ensure_assets()
window.color = color.black

# الخلفية: كرة كبيرة نراها من الداخل (بانورامية من كل الجهات)
sky_tex = load_texture(SKY_FILE)
sky = Entity(model="sphere", scale=500, double_sided=True,
             color=color.white if sky_tex else color.black)
if sky_tex:
    sky.texture = sky_tex
    sky.texture_scale = (SKY_REPEAT, 1)

# ارضية بصورة اصفار وواحدات واسلاك خضراء
floor_tex = load_texture(FLOOR_FILE)
floor = Entity(model="plane", scale=(80, 1, 80), position=(0, 0, 20),
               color=color.white if floor_tex else color.dark_gray,
               collider="mesh")
if floor_tex:
    floor.texture = floor_tex
    floor.texture_scale = (10, 10)

# اطار اخضر حول الارضية
for pos, scl in (((0, 0.05, -20), (80, 0.1, 0.4)), ((0, 0.05, 60), (80, 0.1, 0.4)),
                 ((-40, 0.05, 20), (0.4, 0.1, 80)), ((40, 0.05, 20), (0.4, 0.1, 80))):
    Entity(model="cube", position=pos, scale=scl, color=color.lime)

player = FirstPersonController()
player.traverse_target = scene   # يبحث عن الارض في كل المشهد
BASE_SPEED = player.speed
BASE_FOV = camera.fov
Entity(parent=camera.ui, model="quad", scale=0.008, color=color.white)  # نقطة التصويب

hud = Text(parent=camera.ui, position=window.top_left + Vec2(0.01, -0.01), origin=(-0.5, 0.5))
Text(parent=camera.ui, position=window.bottom_left + Vec2(0.01, 0.04), origin=(-0.5, 0.5),
     text="Double click: open | Right click: menu | Backspace: up | Esc: exit", scale=0.8)
Text(parent=camera.ui, position=window.bottom_left + Vec2(0.01, 0.08), origin=(-0.5, 0.5),
     text="Shift: sprint | T: turbo | G: arrange | K: sky | M: meteor shower | C: comet | Scroll: carry distance",
     scale=0.8)
speed_text = Text(parent=camera.ui, y=-0.42, origin=(0, 0), color=color.azure, scale=1.4)
message = Text(parent=camera.ui, y=0.4, origin=(0, 0), color=color.yellow)

sky_fx_init()
build_world()

app.run()
