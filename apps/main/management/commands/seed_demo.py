import math
import random
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from apps.anime.models import Anime, Genre, Season
from apps.episode.demo import attach_demo_to_episodes
from apps.episode.models import Episode
from apps.users.notices import mute_notices


CATALOG = [
    {
        "title": "Neon Qish",
        "jp": "ネオンの冬",
        "description": "Tokio-2029. Yagona rassom qorong'u shaharni neon chizgilar bilan qutqaradi. Jang, sirlilik va birinchi sevgiga to'la qish.",
        "genres": ["Jangari", "Fantastika"],
        "year": 2025,
        "episodes": 12,
        "kind": "anime",
        "theme": "neon",
        "colors": ("#120028", "#ff2bd6", "#00e5ff"),
    },
    {
        "title": "Oy Ostidagi Qilich",
        "jp": "月下の剣",
        "description": "Qadimgi maktabning oxirgi shogirdi oy nuri bilan qilich chizadi. Demonlar esa har kecha yaqinlashadi.",
        "genres": ["Jangari", "Sarguzasht"],
        "year": 2024,
        "episodes": 24,
        "kind": "anime",
        "theme": "moon",
        "colors": ("#071018", "#7c5cff", "#ffd36a"),
    },
    {
        "title": "Sakura Server",
        "jp": "桜サーバー",
        "description": "Maktab qizi virtual olamda admin bo'lib qoladi. Real hayotdagi dushmanlar login qilishni boshlaydi.",
        "genres": ["Komediya", "Fantastika"],
        "year": 2026,
        "episodes": 8,
        "kind": "anime",
        "theme": "sakura",
        "colors": ("#2a1028", "#ff6ad5", "#ffd1e8"),
    },
    {
        "title": "Qora Poyezd",
        "jp": "黒い列車",
        "description": "Hech qayerga bormaydigan poyezd. Har vagon — boshqa xotira. Chiqish faqat bir juft qo'lda.",
        "genres": ["Sirli", "Dramma"],
        "year": 2023,
        "episodes": 10,
        "kind": "drama",
        "theme": "train",
        "colors": ("#0b0714", "#5b8cff", "#c9d4ff"),
    },
    {
        "title": "Yulduz Ovchisi",
        "jp": "星の狩人",
        "description": "Kichik sayyora qahramoni osmonga chiqib, yo'qolgan yulduzlarni uyiga qaytaradi.",
        "genres": ["Sarguzasht", "Fantastika"],
        "year": 2025,
        "episodes": 13,
        "kind": "anime",
        "theme": "stars",
        "colors": ("#03101c", "#00e5ff", "#7c5cff"),
    },
    {
        "title": "Ikki Qalb",
        "jp": "二つの心",
        "description": "Dushman maktablarning ikki o'quvchisi bir xotiraga bog'lanib qoladi. Sevgi ham, jang ham shu yerda.",
        "genres": ["Romantika", "Dramma"],
        "year": 2024,
        "episodes": 12,
        "kind": "drama",
        "theme": "hearts",
        "colors": ("#1a0818", "#ff4f8b", "#ffd1e0"),
    },
    {
        "title": "Oxirgi Stansiya",
        "jp": "終着駅",
        "description": "Bir kecha — bir poyezd, bir qaror. Qisqa metrli kino: chiqish faqat oxirgi stansiyada.",
        "genres": ["Dramma", "Sirli"],
        "year": 2025,
        "episodes": 1,
        "kind": "film",
        "theme": "train",
        "colors": ("#100814", "#ffd36a", "#5b8cff"),
    },
    {
        "title": "Shahar Soati",
        "jp": "都市の時計",
        "description": "Har kecha 23:00 da shahar vaqti to‘xtaydi. Serial: kim soatni qayta ishga tushirsa, o‘sha yashaydi.",
        "genres": ["Sirli", "Dramma"],
        "year": 2026,
        "episodes": 8,
        "kind": "serial",
        "theme": "neon",
        "colors": ("#0a1220", "#7c5cff", "#00e5ff"),
    },
]


def _rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _font(size, bold=False):
    paths = [
        ("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _jp_font(size):
    for path, index in (
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0),
    ):
        try:
            return ImageFont.truetype(path, size, index=index)
        except (OSError, TypeError):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return _font(size)


def _gradient(size, top, bottom):
    w, h = size
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        draw.line([(0, y), (w, y)], fill=_lerp(top, bottom, y / max(h - 1, 1)))
    return img


def _glow(base, color, box, blur=28):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(box, fill=color + (90,))
    return Image.alpha_composite(base, layer.filter(ImageFilter.GaussianBlur(blur)))


def _stars(draw, w, h, rng, count=90, color=(255, 255, 255)):
    for _ in range(count):
        x = rng.randint(6, w - 6)
        y = rng.randint(8, int(h * 0.58))
        s = rng.choice([1, 1, 1, 2, 2, 3])
        draw.ellipse([x - s, y - s, x + s, y + s], fill=color)
        if s > 2:
            draw.line([(x - 5, y), (x + 5, y)], fill=color, width=1)
            draw.line([(x, y - 5), (x, y + 5)], fill=color, width=1)


def _petals(draw, w, h, rng, color, count=28):
    for _ in range(count):
        x = rng.randint(0, w)
        y = rng.randint(int(h * 0.08), int(h * 0.78))
        r = rng.randint(7, 16)
        draw.ellipse([x, y, x + r, y + int(r * 1.4)], fill=color)
        draw.ellipse([x + 3, y - 2, x + r + 4, y + int(r * 1.1)], fill=color)


def _skyline(draw, w, h, color, window, rng):
    ground = int(h * 0.76)
    x = -10
    while x < w:
        bw = rng.randint(26, 64)
        bh = rng.randint(50, 210)
        draw.rectangle([x, ground - bh, x + bw - 2, h], fill=color)
        wy = ground - bh + 8
        while wy < ground - 8:
            wx = x + 6
            while wx < x + bw - 10:
                if rng.random() > 0.35:
                    draw.rectangle([wx, wy, wx + 5, wy + 7], fill=window)
                wx += 10
            wy += 14
        x += bw


def _character(draw, cx, gy, scale, fill, accent=None, flip=False):
    """gy is the foot line; keep it around 560 so the figure sits above the title bar."""
    s = scale
    dir_ = -1 if flip else 1
    head_r = int(34 * s)
    head_x = cx + dir_ * int(6 * s)
    head_y = gy - int(188 * s)

    def shade(color, a=255):
        return color if len(color) == 4 else color + (a,)

    if accent:
        _character(draw, cx - dir_ * 5, gy - 6, scale, accent, None, flip)

    # Hair mass
    draw.ellipse(
        [head_x - head_r - 8, head_y - head_r - 18, head_x + head_r + 14, head_y + head_r - 4],
        fill=shade(fill),
    )
    # Face
    draw.ellipse(
        [head_x - head_r + 4, head_y - head_r + 6, head_x + head_r - 2, head_y + head_r],
        fill=shade(fill),
    )
    # Short bangs, not a spiky ball
    for i in range(6):
        ang = math.radians(-100 + i * 28)
        x2 = head_x + int(math.cos(ang) * head_r * 1.35)
        y2 = head_y - 6 + int(math.sin(ang) * head_r * 1.25)
        x3 = head_x + int(math.cos(ang + 0.28) * head_r * 0.7)
        y3 = head_y + int(math.sin(ang + 0.28) * head_r * 0.45)
        draw.polygon([(head_x, head_y - 4), (x2, y2), (x3, y3)], fill=shade(fill))
    # Side lock
    draw.polygon(
        [
            (head_x + dir_ * head_r, head_y),
            (head_x + dir_ * int(head_r * 1.6), head_y + int(40 * s)),
            (head_x + dir_ * int(head_r * 0.4), head_y + int(28 * s)),
        ],
        fill=shade(fill),
    )
    neck_w = int(11 * s)
    draw.rectangle(
        [cx - neck_w, head_y + head_r - 4, cx + neck_w, head_y + head_r + int(22 * s)],
        fill=shade(fill),
    )
    top = head_y + head_r + int(14 * s)
    tw, th = int(48 * s), int(92 * s)
    draw.polygon(
        [
            (cx - int(16 * s), top),
            (cx + int(18 * s), top),
            (cx + tw + dir_ * 8, top + th),
            (cx - tw, top + th),
        ],
        fill=shade(fill),
    )
    # Arm
    draw.polygon(
        [
            (cx + dir_ * int(18 * s), top + int(18 * s)),
            (cx + dir_ * int(28 * s), top + int(22 * s)),
            (cx + dir_ * int(62 * s), top + int(88 * s)),
            (cx + dir_ * int(48 * s), top + int(94 * s)),
        ],
        fill=shade(fill),
    )
    # Skirt / coat hem
    draw.polygon(
        [
            (cx - tw, top + th - 4),
            (cx + tw + dir_ * 8, top + th - 4),
            (cx + int(58 * s), gy),
            (cx - int(62 * s), gy),
        ],
        fill=shade(fill),
    )


def _sword(draw, x, y, length, color):
    draw.polygon(
        [(x, y), (x + 14, y + 18), (x + 8, y + length), (x - 6, y + length - 10)],
        fill=color,
    )
    draw.rectangle([x - 18, y + 22, x + 26, y + 30], fill=color)


def _train(draw, w, h, body, window):
    y = int(h * 0.42)
    draw.rounded_rectangle([40, y, w - 40, y + 220], radius=18, fill=body)
    for i in range(4):
        wx = 70 + i * 120
        draw.rounded_rectangle([wx, y + 36, wx + 96, y + 128], radius=10, fill=window)
    draw.rectangle([0, y + 210, w, y + 248], fill=_lerp(body, (0, 0, 0), 0.4))


def _title_block(img, title, jp, accent):
    w, h = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rectangle([0, h - 250, w, h], fill=(6, 2, 18, 210))
    d.polygon([(0, h - 250), (w, h - 290), (w, h - 250)], fill=(6, 2, 18, 210))
    d.rectangle([0, h - 8, w, h], fill=accent + (255,))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    d = ImageDraw.Draw(img)
    jp_font = _jp_font(28)
    title_font = _font(42, bold=True)
    small = _font(18)
    d.text((32, h - 228), jp, fill=accent + (255,), font=jp_font)
    words = title.upper().split()
    line1 = words[0]
    line2 = " ".join(words[1:])
    d.text((32, h - 180), line1, fill=(255, 255, 255, 255), font=title_font)
    if line2:
        d.text((32, h - 132), line2, fill=(255, 255, 255, 255), font=title_font)
        d.text((32, h - 78), "ANIMEE ORIGINAL", fill=(0, 229, 255, 255), font=small)
    else:
        d.text((32, h - 118), "ANIMEE ORIGINAL", fill=(0, 229, 255, 255), font=small)
    return img.convert("RGB")


def _poster_png(item):
    w, h = 600, 840
    bg, accent, second = (_rgb(c) for c in item["colors"])
    rng = random.Random(item["title"])
    img = _gradient((w, h), bg, _lerp(bg, (0, 0, 0), 0.45))
    theme = item["theme"]

    if theme == "neon":
        img = _glow(img.convert("RGBA"), accent, (60, 40, 340, 340), 40)
        img = _glow(img, second, (280, 80, 620, 420), 50)
        draw = ImageDraw.Draw(img)
        _stars(draw, w, h, rng, 70, second)
        _skyline(draw, w, h, _lerp(bg, (20, 0, 40), 0.2), second, rng)
        _character(draw, 410, 555, 1.15, (8, 0, 18), accent)
        draw.rectangle([40, 210, 52, 420], fill=accent)
        draw.rectangle([58, 250, 70, 390], fill=second)
    elif theme == "moon":
        img = _glow(img.convert("RGBA"), accent, (280, -20, 640, 340), 36)
        draw = ImageDraw.Draw(img)
        ImageDraw.Draw(img).ellipse([330, 40, 560, 270], fill=_lerp(accent, (255, 255, 255), 0.55))
        ImageDraw.Draw(img).ellipse([390, 50, 600, 260], fill=bg)
        _stars(draw, w, h, rng, 110, (255, 236, 180))
        _character(draw, 210, 555, 1.2, (10, 8, 22), _rgb("#ffd36a"))
        _sword(draw, 300, 210, 280, _rgb("#ffd36a"))
    elif theme == "sakura":
        img = _glow(img.convert("RGBA"), accent, (80, 40, 420, 380), 34)
        draw = ImageDraw.Draw(img)
        _stars(draw, w, h, rng, 40, (255, 210, 230))
        _character(draw, 340, 555, 1.18, (32, 8, 28), accent)
        _petals(draw, w, h, rng, accent, 40)
        _petals(draw, w, h, rng, second, 18)
    elif theme == "train":
        img = _glow(img.convert("RGBA"), second, (40, 80, 560, 360), 30)
        draw = ImageDraw.Draw(img)
        for i in range(18):
            y = 40 + i * 28
            draw.line([(0, y), (w, y + 40)], fill=_lerp(bg, second, 0.18), width=2)
        _train(draw, w, h, _lerp(bg, (30, 20, 50), 0.5), _lerp(second, (255, 255, 255), 0.2))
        _character(draw, 168, 555, 1.05, (6, 4, 16), second)
    elif theme == "stars":
        img = _glow(img.convert("RGBA"), second, (120, 20, 500, 360), 42)
        draw = ImageDraw.Draw(img)
        _stars(draw, w, h, rng, 160, second)
        for i in range(7):
            x0, y0 = rng.randint(40, 500), rng.randint(40, 280)
            draw.line([(x0, y0), (x0 + 90, y0 + 160)], fill=accent, width=2)
        _character(draw, 300, 555, 0.95, (4, 12, 24), second)
        ImageDraw.Draw(img).ellipse([240, 90, 360, 210], fill=_lerp(second, (255, 255, 255), 0.35))
    else:
        img = _glow(img.convert("RGBA"), accent, (40, 60, 320, 360), 36)
        img = _glow(img, second, (280, 80, 620, 400), 36)
        draw = ImageDraw.Draw(img)
        ImageDraw.Draw(img).ellipse([210, 70, 390, 250], fill=_lerp(second, (255, 255, 255), 0.4))
        _character(draw, 200, 555, 1.12, (28, 6, 22), accent)
        _character(draw, 400, 555, 1.12, (12, 4, 18), second, flip=True)
        _petals(draw, w, h, rng, accent, 22)

    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img = _title_block(img, item["title"], item["jp"], accent)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _thumb_png(poster_bytes):
    img = Image.open(BytesIO(poster_bytes)).convert("RGB")
    w, h = img.size
    crop_h = int(w * 9 / 16)
    top = max(int(h * 0.18), 0)
    box = (0, top, w, min(top + crop_h, h))
    thumb = img.crop(box).resize((480, 270), Image.Resampling.LANCZOS)
    buf = BytesIO()
    thumb.save(buf, format="PNG")
    return buf.getvalue()


class Command(BaseCommand):
    help = "Seed a small Animee catalog so the public UI is not empty."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh-art",
            action="store_true",
            help="Overwrite posters and episode thumbnails even if they already exist.",
        )

    def handle(self, *args, **options):
        refresh = options["refresh_art"]
        with mute_notices():
            self._seed(refresh)

    def _seed(self, refresh):
        for item in CATALOG:
            genre_objs = []
            for name in item["genres"]:
                g, _ = Genre.objects.get_or_create(name=name, defaults={"slug": name.lower()})
                genre_objs.append(g)
            anime, created = Anime.objects.get_or_create(
                title=item["title"],
                defaults={"description": item["description"]},
            )
            anime.description = item["description"]
            anime.kind = item.get("kind", "anime")
            poster_bytes = _poster_png(item)
            if created or refresh or not anime.poster:
                if anime.poster:
                    anime.poster.delete(save=False)
                anime.poster.save(
                    f"{item['title'].lower().replace(' ', '-')}.png",
                    ContentFile(poster_bytes),
                    save=False,
                )
            anime.save()
            anime.genres.set(genre_objs)
            season, _ = Season.objects.get_or_create(
                anime=anime, number=1, defaults={"release_date": item["year"]}
            )
            season.release_date = item["year"]
            season.save()
            thumb_bytes = _thumb_png(poster_bytes)
            for n in range(1, item["episodes"] + 1):
                ep, _ = Episode.objects.get_or_create(
                    season=season,
                    number=n,
                    defaults={"title": f"{n}-qism"},
                )
                if refresh or not ep.thumbnail:
                    if ep.thumbnail:
                        ep.thumbnail.delete(save=False)
                    ep.thumbnail.save(
                        f"{item['title'].lower().replace(' ', '-')}-e{n}.png",
                        ContentFile(thumb_bytes),
                        save=False,
                    )
                    ep.save()
        created, url = attach_demo_to_episodes()
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(CATALOG)} titles."))
        if url:
            self.stdout.write(self.style.SUCCESS(f"{created} ta qismga demo video ({url}) qo‘yildi."))
        else:
            self.stdout.write(self.style.WARNING("demo.mp4 topilmadi — qismlar videosiz qoldi."))
