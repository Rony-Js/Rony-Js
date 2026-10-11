import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

# ============================================================
# CONFIGURACIÓN
# ============================================================
HANDLE = "Rony-js"
ASSETS_DIR = Path("assets/")
CACHE_FILE = ASSETS_DIR / ".cache.json"
CACHE_TTL_HOURS = 6

CF_API = "https://codeforces.com/api"

RANK_COLORS = {
    "newbie": "#808080",
    "pupil": "#008000",
    "specialist": "#03A89E",
    "expert": "#0000FF",
    "candidate master": "#AA00AA",
    "master": "#FF8C00",
    "international master": "#FF8C00",
    "grandmaster": "#FF0000",
    "international grandmaster": "#FF0000",
    "legendary grandmaster": "#FF0000",
    "unrated": "#808080",
}

THEMES = {
    "dark": {
        "bg": "#0D1117",
        "card": "#161B22",
        "border": "#30363D",
        "text": "#F0F6FC",
        "muted": "#8B949E",
        "accent": "#58A6FF",
        "success": "#3FB950",
        "warning": "#F7B100",
    },
    "light": {
        "bg": "#FFFFFF",
        "card": "#F6F8FA",
        "border": "#D0D7DE",
        "text": "#1F2328",
        "muted": "#57606A",
        "accent": "#0969DA",
        "success": "#1A7F37",
        "warning": "#BF8700",
    },
}


# ============================================================
# CACHÉ
# ============================================================
def load_cache():
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        cached_at = datetime.fromisoformat(cache["cached_at"])
        if datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS):
            print("Usando caché reciente.")
            return cache["data"]
    except (json.JSONDecodeError, KeyError, ValueError):
        pass
    return None


def save_cache(data):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"cached_at": datetime.now().isoformat(), "data": data},
            f,
            ensure_ascii=False,
        )


# ============================================================
# API DE CODEFORCES
# ============================================================
def _fetch(endpoint, **params):
    url = f"{CF_API}/{endpoint}"
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "OK":
        raise RuntimeError(f"API error en {endpoint}: {payload.get('comment')}")
    return payload["result"]


def fetch_user_info(handle):
    return _fetch("user.info", handles=handle)[0]


def fetch_submissions(handle):
    return _fetch("user.status", handle=handle, from_=1, count=10000)


def fetch_rating_history(handle):
    try:
        return _fetch("user.rating", handle=handle)
    except RuntimeError:
        return []


# ============================================================
# CÁLCULOS
# ============================================================
def count_solved_problems(submissions):
    solved = set()
    for sub in submissions:
        if sub.get("verdict") == "OK":
            problem = sub.get("problem", {})
            key = (
                f"{problem.get('contestId', '')}-"
                f"{problem.get('index', '')}-"
                f"{problem.get('name', '')}"
            )
            solved.add(key)
    return len(solved)


def normalize_lang(lang):
    """Consolida variantes de un mismo lenguaje (GNU C++20, msys2, etc.)."""
    l = lang.lower()
    if "c++" in l or "g++" in l or "gcc" in l or "msys" in l:
        return "C++"
    if "pypy" in l:
        return "PyPy"
    if "python" in l:
        return "Python"
    if "java" in l and "javascript" not in l:
        return "Java"
    if "kotlin" in l:
        return "Kotlin"
    if "rust" in l:
        return "Rust"
    if "golang" in l or l.strip() == "go":
        return "Go"
    if "c#" in l:
        return "C#"
    return lang.split("(")[0].split(" ")[0].strip() or lang


def top_languages(submissions, top_n=4):
    counts = {}
    for sub in submissions:
        lang = sub.get("programmingLanguage")
        if not lang:
            continue
        key = normalize_lang(lang)
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n]


def daily_streak(submissions):
    """Días consecutivos (hasta hoy o ayer) con al menos un submission."""
    if not submissions:
        return 0
    days = set()
    for sub in submissions:
        ts = sub.get("creationTimeSeconds")
        if ts:
            days.add(datetime.fromtimestamp(ts).date())

    streak = 0
    today = datetime.now().date()
    if today not in days:
        today -= timedelta(days=1)

    while today in days:
        streak += 1
        today -= timedelta(days=1)
    return streak


# ============================================================
# UTILIDADES SVG
# ============================================================
def safe_text(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def shorten(text, limit=18):
    text = safe_text(text)
    return text[:limit] + "..." if len(text) > limit else text


def get_rank_color(rank):
    return RANK_COLORS.get(str(rank).lower(), "#58A6FF")


# ============================================================
# SVG: TARJETA PRINCIPAL
# ============================================================
def generate_card_svg(user, solved_count, streak, languages, theme_name):
    t = THEMES[theme_name]
    handle = user.get("handle", HANDLE)
    full_name = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip() or "Not Set"
    full_name = shorten(full_name, 18)

    rank = user.get("rank", "unrated")
    rating = user.get("rating", "N/A")
    max_rank = user.get("maxRank", "unrated")
    max_rating = user.get("maxRating", "N/A")
    friends = user.get("friendOfCount", 0)
    rank_color = get_rank_color(rank)
    updated = datetime.now().strftime("%Y-%m-%d")

    # Texto de lenguajes (limitado)
    if languages:
        lang_str = "  ·  ".join(f"{name} ({count})" for name, count in languages)
        if len(lang_str) > 80:
            lang_str = lang_str[:77] + "..."
    else:
        lang_str = "No data"

    # Barra proporcional de lenguajes
    lang_bars = ""
    if languages:
        bar_colors = ["#F7B100", "#1F8ACB", "#D9534F", "#8957E5"]
        total = sum(c for _, c in languages) or 1
        gap = 4
        usable = 740 - gap * (len(languages) - 1)
        x = 30
        for i, (_, count) in enumerate(languages):
            width = max(int(usable * (count / total)), 4)
            lang_bars += (
                f'<rect x="{x}" y="282" width="{width}" height="6" rx="3" '
                f'fill="{bar_colors[i % len(bar_colors)]}"/>'
            )
            x += width + gap

    svg = f'''<svg width="800" height="320" viewBox="0 0 800 320" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="800" height="320" rx="22" fill="{t['bg']}"/>
  <rect x="1" y="1" width="798" height="318" rx="22" stroke="{t['border']}" stroke-width="2"/>

  <!-- Logo barras -->
  <rect x="55" y="24" width="10" height="30" rx="2" fill="#F7B100"/>
  <rect x="70" y="14" width="10" height="40" rx="2" fill="#1F8ACB"/>
  <rect x="85" y="29" width="10" height="25" rx="2" fill="#D9534F"/>

  <text x="112" y="52" fill="{t['text']}" font-size="30" font-family="Segoe UI, Arial, sans-serif" font-weight="700">CODEFORCES</text>
  <text x="30" y="78" fill="{t['muted']}" font-size="14" font-family="Segoe UI, Arial, sans-serif">Competitive Programming Progress</text>

  <!-- Card principal -->
  <rect x="30" y="95" width="740" height="130" rx="16" fill="{t['card']}"/>
  <rect x="30" y="95" width="740" height="130" rx="16" stroke="{t['border']}"/>

  <text x="55" y="135" fill="{t['muted']}" font-size="15" font-family="Segoe UI, Arial, sans-serif">Name</text>
  <text x="205" y="135" fill="{t['text']}" font-size="17" font-family="Segoe UI, Arial, sans-serif" font-weight="600">{full_name}</text>

  <text x="55" y="165" fill="{t['muted']}" font-size="15" font-family="Segoe UI, Arial, sans-serif">Handle</text>
  <text x="205" y="165" fill="{t['accent']}" font-size="17" font-family="Segoe UI, Arial, sans-serif" font-weight="700">{safe_text(handle)}</text>

  <text x="55" y="195" fill="{t['muted']}" font-size="15" font-family="Segoe UI, Arial, sans-serif">Friends</text>
  <text x="205" y="195" fill="{t['text']}" font-size="17" font-family="Segoe UI, Arial, sans-serif" font-weight="600">{friends}</text>

  <text x="490" y="135" fill="{t['muted']}" font-size="15" font-family="Segoe UI, Arial, sans-serif">Rating</text>
  <text x="620" y="135" fill="{rank_color}" font-size="17" font-family="Segoe UI, Arial, sans-serif" font-weight="700">{rating} ({safe_text(rank)})</text>

  <text x="490" y="165" fill="{t['muted']}" font-size="15" font-family="Segoe UI, Arial, sans-serif">Max Rating</text>
  <text x="620" y="165" fill="{t['text']}" font-size="17" font-family="Segoe UI, Arial, sans-serif" font-weight="600">{max_rating} ({safe_text(max_rank)})</text>

  <text x="490" y="195" fill="{t['muted']}" font-size="15" font-family="Segoe UI, Arial, sans-serif">Solved</text>
  <text x="620" y="195" fill="{t['accent']}" font-size="18" font-family="Segoe UI, Arial, sans-serif" font-weight="700">{solved_count}</text>

  <!-- Fila 1: racha -->
  <text x="30" y="252" fill="{t['muted']}" font-size="13" font-family="Segoe UI, Arial, sans-serif">🔥 Streak: {streak} day{'s' if streak != 1 else ''}</text>

  <!-- Fila 2: lenguajes -->
  <text x="30" y="272" fill="{t['muted']}" font-size="13" font-family="Segoe UI, Arial, sans-serif">Top languages: {safe_text(lang_str)}</text>

  <!-- Barra proporcional -->
  {lang_bars}

  <!-- Fila 3: updated -->
  <text x="30" y="308" fill="{t['muted']}" font-size="12" font-family="Segoe UI, Arial, sans-serif">Updated: {updated} • Keep solving, keep improving.</text>
</svg>'''
    return svg


# ============================================================
# SVG: GRÁFICO DE RATING
# ============================================================
def generate_rating_svg(rating_history, theme_name):
    t = THEMES[theme_name]
    width, height = 800, 260
    pad_l, pad_r, pad_t, pad_b = 60, 30, 50, 40
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    empty_svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <rect width="{width}" height="{height}" rx="22" fill="{t['bg']}"/>
      <rect x="1" y="1" width="{width-2}" height="{height-2}" rx="22" stroke="{t['border']}" stroke-width="2"/>
      <text x="400" y="140" text-anchor="middle" fill="{t['muted']}" font-family="Segoe UI, Arial" font-size="16">No rating history yet</text>
    </svg>'''

    # La API devuelve: newRating, oldRating, ratingUpdateTimeSeconds, ...
    points = [
        (c["newRating"], c.get("ratingUpdateTimeSeconds", 0))
        for c in rating_history
        if "newRating" in c and c.get("ratingUpdateTimeSeconds")
    ]

    if len(points) < 2:
        return empty_svg

    ratings = [p[0] for p in points]
    min_r, max_r = min(ratings), max(ratings)
    span = max(max_r - min_r, 1)

    coords = []
    for i, (r, _) in enumerate(points):
        x = pad_l + (i / (len(points) - 1)) * plot_w
        y = pad_t + plot_h - ((r - min_r) / span) * plot_h
        coords.append((x, y))

    path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = path + f" L {coords[-1][0]:.1f},{pad_t + plot_h} L {coords[0][0]:.1f},{pad_t + plot_h} Z"

    circles = ""
    for (x, y), (r, _) in zip(coords, points):
        color = "#808080"
        if r >= 2400:
            color = "#FF0000"
        elif r >= 2100:
            color = "#FF8C00"
        elif r >= 1900:
            color = "#AA00AA"
        elif r >= 1600:
            color = "#0000FF"
        elif r >= 1400:
            color = "#03A89E"
        elif r >= 1200:
            color = "#008000"
        circles += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>'

    last_rating = ratings[-1]
    last_date = datetime.fromtimestamp(points[-1][1]).strftime("%Y-%m-%d")

    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="22" fill="{t['bg']}"/>
  <rect x="1" y="1" width="{width-2}" height="{height-2}" rx="22" stroke="{t['border']}" stroke-width="2"/>

  <text x="30" y="32" fill="{t['text']}" font-size="18" font-family="Segoe UI, Arial" font-weight="700">Rating History</text>
  <text x="{width-30}" y="32" text-anchor="end" fill="{t['accent']}" font-size="16" font-family="Segoe UI, Arial" font-weight="700">{last_rating}</text>

  <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" stroke="{t['border']}"/>
  <line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h}" stroke="{t['border']}"/>

  <path d="{area}" fill="{t['accent']}" opacity="0.15"/>
  <path d="{path}" stroke="{t['accent']}" stroke-width="2.5" fill="none" stroke-linejoin="round"/>

  {circles}

  <text x="{pad_l - 10}" y="{pad_t + 5}" text-anchor="end" fill="{t['muted']}" font-size="12" font-family="Segoe UI, Arial">{max_r}</text>
  <text x="{pad_l - 10}" y="{pad_t + plot_h}" text-anchor="end" fill="{t['muted']}" font-size="12" font-family="Segoe UI, Arial">{min_r}</text>

  <text x="30" y="{height-12}" fill="{t['muted']}" font-size="12" font-family="Segoe UI, Arial">Contests: {len(points)} • Last update: {last_date}</text>
</svg>'''
    return svg


# ============================================================
# ESCRITURA SEGURA
# ============================================================
def safe_write(path, content):
    path = Path(path)
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if old == content:
            print(f"Sin cambios en {path}")
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"✓ Generado {path}")


# ============================================================
# MAIN
# ============================================================
def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    cached = load_cache()
    if cached:
        user = cached["user"]
        rating_history = cached["rating_history"]
        solved_count = cached["solved_count"]
        streak = cached["streak"]
        languages = cached["languages"]
    else:
        print("Consultando API de Codeforces...")
        try:
            user = fetch_user_info(HANDLE)
            submissions = fetch_submissions(HANDLE)
            rating_history = fetch_rating_history(HANDLE)
        except Exception as e:
            print(f"⚠️ Error al consultar la API: {e}")
            sys.exit(1)

        solved_count = count_solved_problems(submissions)
        streak = daily_streak(submissions)
        languages = top_languages(submissions)

        save_cache({
            "user": user,
            "rating_history": rating_history,
            "solved_count": solved_count,
            "streak": streak,
            "languages": languages,
        })

    # Tarjeta principal en ambos temas
    safe_write(
        ASSETS_DIR / "codeforces-stats-dark.svg",
        generate_card_svg(user, solved_count, streak, languages, "dark"),
    )
    safe_write(
        ASSETS_DIR / "codeforces-stats-light.svg",
        generate_card_svg(user, solved_count, streak, languages, "light"),
    )

    # Gráfico de rating en ambos temas
    safe_write(
        ASSETS_DIR / "codeforces-rating-dark.svg",
        generate_rating_svg(rating_history, "dark"),
    )
    safe_write(
        ASSETS_DIR / "codeforces-rating-light.svg",
        generate_rating_svg(rating_history, "light"),
    )


if __name__ == "__main__":
    main()
