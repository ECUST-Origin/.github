"""Render the ECUST ORIGIN dashboard PNG (black + gold, low-sat icons).

Reads data/repos.json (produced by fetch_data.py) and writes
assets/dashboard.png. Pure Pillow, plus optional cairosvg to fetch
official Simple Icons for the tech-stack pills (downloaded once and
cached under assets/icons/, then desaturated to ICON_GRAY).

If no data is found, falls back to mock data so the pipeline always
produces a valid PNG. If cairosvg (or libcairo) is unavailable, the
stack pills degrade to first-letter monograms rather than crashing.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    import requests
except ImportError:  # optional: only needed for live member avatars
    requests = None  # type: ignore

# cairosvg's cffi backend lazily loads libcairo; if the system library
# is missing (common on Windows) import succeeds but every call raises
# OSError. Treat both as "cairosvg unavailable".
try:
    import cairosvg as _cairosvg  # noqa: F401
    cairosvg = _cairosvg
    cairosvg_available = True
except Exception:
    cairosvg = None  # type: ignore
    cairosvg_available = False


# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #
BG          = (10, 10, 10)         # #0a0a0a
CARD_BG     = (20, 20, 20)         # #141414
GOLD        = (201, 169, 97)       # #c9a961
GOLD_DARK   = (138, 116, 55)       # #8a7437
GOLD_DIM    = (58, 51, 32)         # #3a3320
TEXT        = (232, 232, 232)      # #e8e8e8
TEXT_DIM    = (154, 154, 154)      # #9a9a9a
ICON_GRAY   = (122, 122, 122)      # #7a7a7a
DIVIDER     = (42, 37, 32)         # #2a2520
ACCENT_RED  = (122, 40, 40)        # #7a2828
GREEN_OK    = (180, 140, 60)       # desaturated gold (no pure green)

# Heatmap 5 tiers
HEAT = [
    (26, 26, 26),       # 0
    (58, 51, 32),       # 1-3
    (107, 90, 44),      # 4-7
    (164, 138, 62),     # 8-15
    (201, 169, 97),     # 16+
]

# Language -> desaturated swatch color (no full saturation)
LANG_COLORS = {
    "C":         (140, 140, 130),
    "C++":       (140, 110,  70),
    "Python":    (130, 130, 100),
    "TypeScript":( 90, 110, 130),
    "JavaScript":(130, 120,  80),
    "Go":        ( 90, 120, 130),
    "Rust":      (130,  90,  70),
    "Java":      (130, 100,  80),
    "Shell":     (110, 110, 110),
    "HTML":      (130, 100,  70),
    "CSS":       (100, 110, 130),
    "SolidWorks":(140,  80,  80),
    "CAD":       (140,  80,  80),
}


# Stack label -> Simple Icons slug. None means no official icon; the
# pill will be drawn with a first-letter monogram instead.
SI_VERSION = "16.28.0"
SI_BASE = (
    f"https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@{SI_VERSION}/icons"
)
STACK_ICONS: dict[str, str | None] = {
    "C":          "c",
    "C++":        "cplusplus",
    "Python":     "python",
    "TypeScript": "typescript",
    "STM32":      "stmicroelectronics",   # SI has no STM32; use ST parent
    "OpenCV":     "opencv",
    "FreeRTOS":   None,                    # SI has no FreeRTOS
    "ROS":        "ros",
    "SolidWorks": "dassaultsystemes",      # SI has no SolidWorks; use parent
    "Linux":      "linux",
}
ICON_PX = 18  # rendered icon size for stack pills


# --------------------------------------------------------------------------- #
# Fonts
# --------------------------------------------------------------------------- #
def _font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    candidates: list[str] = []
    if mono:
        candidates += ["JetBrainsMono-Bold.ttf" if bold else "JetBrainsMono-Regular.ttf",
                       "consolab.ttf" if bold else "consola.ttf"]
    else:
        candidates += ["SourceHanSansSC-Bold.otf" if bold else "SourceHanSansSC-Regular.otf",
                       "msyhbd.ttc" if bold else "msyh.ttc",
                       "NotoSansCJK-Bold.ttc" if bold else "NotoSansCJK-Regular.ttc",
                       "arialbd.ttf" if bold else "arial.ttf",
                       "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


# --------------------------------------------------------------------------- #
# Mock data fallback
# --------------------------------------------------------------------------- #
def _mock_data() -> dict[str, Any]:
    today = datetime.now(timezone.utc).date()
    heat = [0] * 364
    for i, d in enumerate(heat):
        # synthetic: stronger in recent months, weekend dip
        wd = (today - timedelta(days=363 - i)).weekday()
        base = (i % 30) % 5
        if wd >= 5:
            heat[i] = max(0, (base * 2) - 3)
        else:
            heat[i] = min(20, base * 4 + (i % 7))
    return {
        "team": {
            "name_en": "ECUST ORIGIN",
            "name_zh": "起源 ORIGIN",
            "slogan": "起源足下 · 不见高山",
            "university": "华东理工大学",
            "department": "机械与动力工程学院 / 大学生创新创业中心",
            "founded": "2024",
            "season": "RoboMaster 2026",
            "stage": "备赛中",
        },
        "stack": ["C", "C++", "Python", "TypeScript", "STM32", "OpenCV",
                  "FreeRTOS", "ROS", "SolidWorks", "Linux"],
        "recruit": {
            "status": "招新中",
            "signup": "春季学期开放",
            "public_account": "起源ORIGIN",
            "qq_group": "待补充",
            "email": "ecust.origin@example.com",
            "website": "https://ecust-origin.github.io",
            "address": "上海市徐汇区梅陇路 130 号",
        },
        "repos": [
            {"name": "origin-infantry",  "stars": 142, "language": "C++",
             "desc": "步兵机器人主控", "url": "#"},
            {"name": "origin-vision",    "stars":  98, "language": "Python",
             "desc": "自瞄与能量机关视觉", "url": "#"},
            {"name": "origin-sentry",    "stars":  76, "language": "C++",
             "desc": "哨兵自主决策", "url": "#"},
            {"name": "origin-website",   "stars":  54, "language": "TypeScript",
             "desc": "战队官网与招新系统", "url": "#"},
            {"name": "origin-mechanical","stars":  33, "language": "SolidWorks",
             "desc": "整机机械图纸", "url": "#"},
        ],
        "members": [
            {"login": "alice",   "avatar_url": "", "commits": 428},
            {"login": "bob",     "avatar_url": "", "commits": 312},
            {"login": "charlie", "avatar_url": "", "commits": 245},
            {"login": "diana",   "avatar_url": "", "commits": 168},
            {"login": "evan",    "avatar_url": "", "commits": 112},
        ],
        "heatmap": heat,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------------- #
# Drawing helpers
# --------------------------------------------------------------------------- #
def _round_rect(draw: ImageDraw.ImageDraw, xy, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _load_stack_icons(stack: list[str], cache_dir: Path) -> dict[str, Image.Image | None]:
    """Fetch official Simple Icons SVGs for each stack label and render
    them as desaturated ICON_GRAY PNGs.

    Returns a mapping label -> PIL Image (RGBA, ICON_PX x ICON_PX), or None
    if the icon is unavailable (no slug, network failure, missing cairosvg).
    """
    out: dict[str, Image.Image | None] = {name: None for name in stack}
    if not stack or not cairosvg_available or requests is None:
        return out
    cache_dir.mkdir(parents=True, exist_ok=True)
    for name in stack:
        slug = STACK_ICONS.get(name)
        if not slug:
            continue
        svg_path = cache_dir / f"{slug}.svg"
        try:
            if not svg_path.exists():
                r = requests.get(f"{SI_BASE}/{slug}.svg", timeout=10,
                                 headers={"User-Agent": "ecust-origin-dashboard"})
                if r.status_code != 200 or not r.content:
                    continue
                svg_path.write_bytes(r.content)
            png_bytes = cairosvg.svg2png(
                bytestring=svg_path.read_bytes(),
                output_width=ICON_PX * 4,
                output_height=ICON_PX * 4,
            )
            from io import BytesIO
            im = Image.open(BytesIO(png_bytes)).convert("RGBA")
            im = im.resize((ICON_PX, ICON_PX), Image.LANCZOS)
            gray = im.convert("LA").convert("RGBA")
            _, _, _, alpha = gray.split()
            solid = Image.new("RGBA", gray.size, ICON_GRAY + (255,))
            out[name] = Image.composite(
                solid, Image.new("RGBA", gray.size, (0, 0, 0, 0)), alpha
            )
        except Exception:
            continue
    return out


def _text_w(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_text(draw, xy, text, font, fill):
    draw.text(xy, text, font=font, fill=fill)


def _measure(draw, text, font):
    return _text_w(draw, text, font)


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
W, H = 1500, 900
MARGIN = 40


def draw_hero(img: Image.Image, draw: ImageDraw.ImageDraw, team: dict) -> int:
    y0 = MARGIN
    f_title = _font(54, bold=True)
    f_sub   = _font(22, bold=False)
    f_meta  = _font(16, bold=False)

    # Logo
    logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
    logo_offset_x = 0
    if logo_path.exists():
        logo = Image.open(logo_path).resize((80, 80))
        # Gold border around logo
        border = Image.new("RGBA", (84, 84), GOLD_DARK)
        border.paste(logo, (2, 2))
        img.paste(border, (MARGIN, y0 + 2), border)
        logo_offset_x = 96

    title = team.get("name_en", "ECUST ORIGIN")
    _draw_text(draw, (MARGIN + logo_offset_x, y0), title, f_title, GOLD)

    # tagline — reduced gap from title/logo
    slogan = team.get("slogan", "")
    _draw_text(draw, (MARGIN + logo_offset_x, y0 + 80), slogan, f_sub, TEXT)

    # right side meta — lower to clear title
    season = team.get("season", "")
    stage  = team.get("stage", "")
    right_text = f"{season}  ·  {stage}"
    rw, _ = _measure(draw, right_text, f_sub)
    _draw_text(draw, (W - MARGIN - rw, y0 + 50), right_text, f_sub, GOLD_DARK)

    # university / department — tighter gap from slogan
    sub2 = f"{team.get('university','')}  ·  {team.get('department','')}"
    _draw_text(draw, (MARGIN + logo_offset_x, y0 + 115), sub2, f_meta, TEXT_DIM)

    # horizontal gold rule — tighter gap from university line
    rule_y = y0 + 148
    draw.line([(MARGIN, rule_y), (W - MARGIN, rule_y)], fill=GOLD_DARK, width=1)
    # accent dash
    draw.line([(MARGIN, rule_y), (MARGIN + 80, rule_y)], fill=GOLD, width=2)

    return rule_y + 40


def draw_three_cards(img, draw, y, data, icons=None) -> int:
    card_h = 150
    gap = 16
    card_w = (W - MARGIN * 2 - gap * 2) // 3
    titles = ["技术栈 · STACK", "战队信息 · TEAM", "招新 · RECRUIT"]
    bodies: list[list[tuple[str, str]]] = [
        [],   # stack drawn specially
        [("成立", data["team"].get("founded", "—")),
         ("学院", data["team"].get("department", "—")),
         ("赛季", data["team"].get("season", "—")),
         ("阶段", data["team"].get("stage", "—"))],
        [("状态", data["recruit"].get("status", "—")),
         ("报名", data["recruit"].get("signup", "—")),
         ("公众号", data["recruit"].get("public_account", "—")),
         ("邮箱", data["recruit"].get("email", "—"))],
    ]
    f_title = _font(16, bold=True)
    f_body  = _font(15, bold=False)
    f_kv_k  = _font(13, bold=False)
    f_kv_v  = _font(15, bold=False)
    f_icon  = _font(22, bold=True)

    for i in range(3):
        x = MARGIN + i * (card_w + gap)
        _round_rect(draw, (x, y, x + card_w, y + card_h), 8, fill=CARD_BG, outline=DIVIDER, width=1)
        _draw_text(draw, (x + 16, y + 14), titles[i], f_title, GOLD)

        if i == 0:
            # stack — official Simple Icons (desaturated gray) + name, 4 cols
            stack = data.get("stack", [])
            icons = icons or {}
            px = x + 16
            py = y + 50
            pill_w = 96
            pill_h = 28
            gap_h = 8
            gap_v = 6
            col_count = 4
            for k, name in enumerate(stack[:10]):
                r = k // col_count
                c = k % col_count
                cx = px + c * (pill_w + gap_h)
                cy = py + r * (pill_h + gap_v)
                # background pill
                _round_rect(draw, (cx, cy, cx + pill_w, cy + pill_h), 4,
                            fill=(28, 28, 28), outline=DIVIDER)
                # icon (Simple Icons) or fallback dot
                icon = icons.get(name)
                icon_size = ICON_PX
                ix = cx + 8
                iy = cy + (pill_h - icon_size) // 2
                if icon is not None:
                    img.paste(icon, (ix, iy), icon)
                else:
                    # Fallback: first-letter monogram in a rounded square
                    mono = (name[:1] or "?").upper()
                    col = LANG_COLORS.get(name, (100, 100, 100))
                    _round_rect(draw,
                                (ix, iy, ix + icon_size, iy + icon_size),
                                4, fill=col, outline=None)
                    bbox = draw.textbbox((0, 0), mono, f_kv_v)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    _draw_text(draw,
                               (ix + (icon_size - tw) // 2,
                                iy + (icon_size - th) // 2 - 1),
                               mono, f_kv_v, BG)
                # name
                text_x = ix + icon_size + 6
                _draw_text(draw, (text_x, cy + (pill_h - 16) // 2), name, f_kv_v, ICON_GRAY)
        else:
            for k, (kk, vv) in enumerate(bodies[i]):
                yy = y + 46 + k * 24
                _draw_text(draw, (x + 16, yy), kk, f_kv_k, TEXT_DIM)
                # truncate long values
                max_v = card_w - 90
                vv_str = vv
                while _measure(draw, vv_str, f_kv_v)[0] > max_v and len(vv_str) > 2:
                    vv_str = vv_str[:-1]
                if vv_str != vv:
                    vv_str = vv_str[:-1] + "…"
                _draw_text(draw, (x + 72, yy), vv_str, f_kv_v, TEXT)

    return y + card_h + 24


def draw_heatmap_and_rank(img, draw, y, data, avatars=None) -> int:
    section_h = 420
    gap = 16
    left_w = int((W - MARGIN * 2 - gap) * 0.55)
    right_w = (W - MARGIN * 2) - left_w - gap

    # Left: heatmap card
    lx, ly = MARGIN, y
    _round_rect(draw, (lx, ly, lx + left_w, ly + section_h), 8, fill=CARD_BG, outline=DIVIDER, width=1)
    _draw_text(draw, (lx + 16, ly + 14), "提交热力图 · COMMIT ACTIVITY", _font(16, bold=True), GOLD)

    draw_heatmap(draw, lx + 16, ly + 72, left_w - 32, section_h - 86, data.get("heatmap", []))

    # summary line at bottom of left card
    heat = data.get("heatmap", [])
    total = sum(heat)
    week = sum(heat[-7:]) if heat else 0
    top_mem = data["members"][0]["login"] if data.get("members") else "—"
    top_cnt = data["members"][0]["commits"] if data.get("members") else 0
    summary = f"总计 {total} commits   ·   本周 {week}   ·   最活跃 {top_mem} ({top_cnt})"
    _draw_text(draw, (lx + 16, ly + section_h - 54), summary, _font(14, bold=False), TEXT_DIM)

    # Right: two stacked sub-cards (no outer border, divider in between)
    rx, ry = MARGIN + left_w + gap, y
    sub1_h = int(section_h * 0.45) - 6
    sub2_h = section_h - sub1_h - 12

    draw_repo_card(draw, rx, ry, right_w, sub1_h, data.get("repos", []))
    draw_member_card(draw, rx, ry + sub1_h + 12, right_w, sub2_h, data.get("members", []), avatars=avatars, img=img)

    return y + section_h + 24


def _tier(n: int) -> int:
    if n <= 0:  return 0
    if n <= 3:  return 1
    if n <= 7:  return 2
    if n <= 15: return 3
    return 4


def draw_heatmap(draw, x, y, w, h, heat):
    days = 364
    weeks = (days + 6) // 7
    pad = 3

    # Determine cell size from the tighter of width or height constraints
    max_cell_by_width = (w - 24) // weeks - pad
    max_cell_by_height = (h - 16 - 36 - pad) // 7

    cell = min(max_cell_by_width, max_cell_by_height, 28)
    cell = max(3, cell)

    grid_w = weeks * (cell + pad) - pad
    grid_h = 7 * (cell + pad) - pad

    # Center grid horizontally; leave left margin for weekday labels
    ox = x + 4
    grid_top = y + 14 + (h - 16 - 36 - grid_h) // 2

    f_month = _font(11, bold=False)
    f_wd    = _font(11, bold=False)
    f_legend = _font(12, bold=False)

    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)

    # month labels (above grid)
    last_label_month = -1
    for w_i in range(weeks):
        d = start + timedelta(days=w_i * 7)
        if d.month != last_label_month and d.day <= 7:
            _draw_text(draw, (ox + w_i * (cell + pad) - 2, grid_top - 14), f"{d.month:02d}", f_month, TEXT_DIM)
            last_label_month = d.month

    # weekday labels (left)
    for r, label in enumerate(["Mon", "Wed", "Fri"]):
        row = [0, 2, 4][r]
        _draw_text(draw, (ox - 28, grid_top + row * (cell + pad) + 1), label, f_wd, TEXT_DIM)

    # cells
    for i, n in enumerate(heat):
        if i >= days:
            break
        r = i % 7
        c = i // 7
        cx = ox + c * (cell + pad)
        cy = grid_top + r * (cell + pad)
        color = HEAT[_tier(n)]
        _round_rect(draw, (cx, cy, cx + cell, cy + cell), 2, fill=color, outline=BG, width=1)

    # legend (below grid)
    leg_y = grid_top + grid_h + 10
    _draw_text(draw, (x, leg_y), "Less", f_legend, TEXT_DIM)
    lx = x + 38
    for k, col in enumerate(HEAT):
        _round_rect(draw, (lx + k * (cell + 4), leg_y, lx + k * (cell + 4) + cell, leg_y + cell),
                    2, fill=col, outline=BG)
    _draw_text(draw, (lx + len(HEAT) * (cell + 4) + 4, leg_y), "More", f_legend, TEXT_DIM)

    # date range (bottom-right)
    range_text = f"{start.isoformat()}  →  {today.isoformat()}"
    rw, _ = _measure(draw, range_text, f_legend)
    _draw_text(draw, (x + w - rw, leg_y), range_text, f_legend, TEXT_DIM)


def draw_repo_card(draw, x, y, w, h, repos):
    _round_rect(draw, (x, y, x + w, y + h), 8, fill=CARD_BG, outline=DIVIDER, width=1)
    _draw_text(draw, (x + 16, y + 12), "仓库排行 · TOP REPOS", _font(15, bold=True), GOLD)
    f_rank = _font(16, bold=True)
    f_name = _font(14, bold=True)
    f_meta = _font(12, bold=False)
    f_star = _font(14, bold=True)

    row_h = (h - 50) // max(1, min(len(repos), 5))
    if row_h < 28:
        row_h = 28
    for i, r in enumerate(repos[:5]):
        ry = y + 40 + i * row_h
        # rank
        _draw_text(draw, (x + 16, ry), f"{i+1:02d}", f_rank, GOLD)
        # name
        _draw_text(draw, (x + 50, ry + 2), r["name"], f_name, TEXT)
        # lang swatch
        col = LANG_COLORS.get(r["language"], (100, 100, 100))
        swatch_x = x + 50 + _measure(draw, r["name"], f_name)[0] + 8
        draw.rectangle((swatch_x, ry + 8, swatch_x + 8, ry + 16), fill=col)
        # desc
        _draw_text(draw, (x + 50, ry + 20), r.get("desc", ""), f_meta, TEXT_DIM)
        # stars
        star_text = f"★ {r['stars']}"
        sw, _ = _measure(draw, star_text, f_star)
        _draw_text(draw, (x + w - 16 - sw, ry + 2), star_text, f_star, GOLD)


def _load_member_avatars(members: list[dict[str, Any]], target: int = 32) -> dict[str, Image.Image | None]:
    """Download each member's avatar, resize, and desaturate to the gold-gray palette.

    Returns a mapping login -> PIL Image (RGBA, square, target x target), or None
    if the avatar could not be fetched.  Failures are silent; we just draw the
    letter placeholder.
    """
    out: dict[str, Image.Image | None] = {}
    if requests is None:
        return {m["login"]: None for m in members}
    for m in members:
        url = m.get("avatar_url") or ""
        login = m.get("login", "?")
        out[login] = None
        if not url:
            continue
        try:
            r = requests.get(url, params={"s": str(target * 2)}, timeout=10,
                             headers={"User-Agent": "ecust-origin-dashboard"})
            if r.status_code != 200 or not r.content:
                continue
            from io import BytesIO
            im = Image.open(BytesIO(r.content)).convert("RGBA")
            im = im.resize((target, target), Image.LANCZOS)
            out[login] = im
        except Exception:
            out[login] = None
    return out


def draw_member_card(draw, x, y, w, h, members, avatars=None, img=None):
    _round_rect(draw, (x, y, x + w, y + h), 8, fill=CARD_BG, outline=DIVIDER, width=1)
    _draw_text(draw, (x + 16, y + 12), "成员贡献 · CONTRIBUTORS", _font(15, bold=True), GOLD)
    f_name   = _font(14, bold=True)
    f_count  = _font(14, bold=True)
    f_bar_lbl= _font(11, bold=False)

    if not members:
        _draw_text(draw, (x + 16, y + 44), "(暂无数据)", f_name, TEXT_DIM)
        return

    max_c = max(m["commits"] for m in members[:5]) or 1
    row_h = (h - 50) // min(len(members), 5)
    if row_h < 36:
        row_h = 36

    for i, m in enumerate(members[:5]):
        ct = str(m["commits"])
        cw, _ = _measure(draw, ct, f_count)
        ry = y + 38 + i * row_h
        # avatar
        avatar = (avatars or {}).get(m["login"]) if avatars else None
        if avatar is not None:
            img.paste(avatar, (x + 16, ry), avatar)
        else:
            draw.ellipse((x + 16, ry, x + 48, ry + 32), fill=ICON_GRAY, outline=DIVIDER)
            _draw_text(draw, (x + 26, ry + 8), (m["login"][:1] or "?").upper(), _font(14, bold=True), BG)
        # name
        _draw_text(draw, (x + 56, ry + 6), f"@{m['login']}", f_name, TEXT)
        # bar — starts after name, ends before count
        name_w, _ = _measure(draw, f"@{m['login']}", f_name)
        bar_start = x + 56 + name_w + 12
        bar_end_max = x + w - 16 - cw - 12
        bar_max_width = bar_end_max - bar_start
        if bar_max_width <= 0:
            bar_max_width = 40  # fallback
        bw = int(bar_max_width * (m["commits"] / max_c))
        _round_rect(draw, (bar_start, ry + 10, bar_start + bw, ry + 20), 3, fill=GOLD, outline=None)
        _round_rect(draw, (bar_start + bw, ry + 10, bar_end_max, ry + 20), 3, fill=(35, 32, 24), outline=None)
        # count
        _draw_text(draw, (x + w - 16 - cw, ry + 6), ct, f_count, GOLD)


def draw_footer(img, draw, y, fetched_at):
    f_text = _font(13, bold=False)
    try:
        dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        stamp = dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    left = "© ECUST ORIGIN  ·  起源足下  ·  不见高山"
    right = f"更新于 {stamp}  ·  Auto-refreshed by GitHub Action"
    lw, _ = _measure(draw, left, f_text)
    rw, _ = _measure(draw, right, f_text)
    _draw_text(draw, (MARGIN, y), left, f_text, TEXT_DIM)
    _draw_text(draw, (W - MARGIN - rw, y), right, f_text, TEXT_DIM)
    # gold accent line
    draw.line([(MARGIN, y - 10), (W - MARGIN, y - 10)], fill=DIVIDER, width=1)
    draw.line([(MARGIN, y - 10), (MARGIN + 60, y - 10)], fill=GOLD, width=2)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def load_data(path: Path) -> dict[str, Any]:
    if not path.exists():
        print(f"[render] {path} not found, using mock data", file=sys.stderr)
        return _mock_data()
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def render(data_path: Path, out_path: Path) -> None:
    data = load_data(data_path)
    avatars = _load_member_avatars(data.get("members", [])) if data.get("members") else {}
    icon_cache_dir = out_path.parent.parent / "assets" / "icons"
    icons = _load_stack_icons(data.get("stack", []), icon_cache_dir)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    y = MARGIN
    y = draw_hero(img, draw, data["team"]) + 8
    y = draw_three_cards(img, draw, y, data, icons=icons)
    y = draw_heatmap_and_rank(img, draw, y, data, avatars=avatars)
    draw_footer(img, draw, H - MARGIN + 4, data.get("fetched_at", ""))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    print(f"[render] wrote {out_path} ({out_path.stat().st_size} bytes)")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/repos.json")
    ap.add_argument("--out", default="assets/dashboard.png")
    args = ap.parse_args()
    render(Path(args.data), Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
