"""Pengelolaan foto panorama geografis dan alam asli beresolusi tinggi untuk 514 kabupaten/kota."""
import json
import time
import urllib.parse
import urllib.request

from django.db import DatabaseError
from django.templatetags.static import static

_BLACKLIST_KEYWORDS = (
    "lambang", "logo", "coat_of_arms", "coat of arms", "emblem", "seal",
    "flag", "bendera", "peta", "map", "locator", "lokasi", "administrative",
    "kecamatan", "diagram", "chart", "icon", "simbol", "kantor_bupati",
    "kantor_walikota", "monumen", "tugu", "patung", "bupati", "walikota",
    "gubernur", "wakil", "svg", "commons-logo", "wikidata", "ambox",
    "tropenmuseum", "collectie", "19", "18",
)

_NATURE_BONUS = (
    "pantai", "beach", "laut", "sea", "teluk", "bay", "pesisir", "coast",
    "gunung", "mount", "mountain", "bukit", "hill", "pegunungan", "ridge",
    "danau", "lake", "sungai", "river", "lembah", "valley", "hutan", "forest",
    "sawah", "rice", "kebun", "plantation", "panorama", "landscape", "alam",
    "nature", "view", "sunset", "sunrise", "pulau", "island", "air_terjun",
    "waterfall", "kawah", "crater", "savana", "savanna", "mangrove", "sabanase",
    "rotiklot", "kelabba", "gayo", "losari",
)


def _nama_valid_untuk_panorama(title_or_url):
    low = title_or_url.lower()
    if ".svg" in low:
        return False
    if not any(ext in low for ext in (".jpg", ".jpeg", ".webp")):
        return False
    return not any(bad in low for bad in _BLACKLIST_KEYWORDS)


def _skor_judul(title):
    low = title.lower()
    return sum(10 for kw in _NATURE_BONUS if kw in low)


def _cek_resolusi_dan_pilih(titles, lang="id"):
    """Memverifikasi ukuran asli gambar via MediaWiki API (min 800px, rasio lanskap >= 1.25)."""
    if not titles:
        return None
    params = urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "titles": "|".join(titles[:10]),
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": "1280",
    })
    url = f"https://{lang}.wikipedia.org/w/api.php?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "RenewableEnergySPK/1.0 (contact@example.org)"})
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    kandidat = []
    for p in (data.get("query") or {}).get("pages", {}).values():
        title = p.get("title") or ""
        infos = p.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        w = info.get("width") or 0
        h = info.get("height") or 0
        mime = (info.get("mime") or "").lower()
        img_url = info.get("thumburl") or info.get("url") or ""
        if "jpeg" not in mime and "webp" not in mime:
            continue
        if w < 800 or h <= 0 or (w / h) < 1.25:
            continue
        if not (_nama_valid_untuk_panorama(title) and _nama_valid_untuk_panorama(img_url)):
            continue
        skor = _skor_judul(title) + (5 if w >= 1200 else 0)
        kandidat.append((skor, w, img_url))

    if not kandidat:
        return None
    kandidat.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return kandidat[0][2]


def _cari_media_wikipedia(judul, lang="id"):
    slug = urllib.parse.quote(judul.replace(" ", "_"), safe="")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/media-list/{slug}"
    req = urllib.request.Request(url, headers={"User-Agent": "RenewableEnergySPK/1.0 (contact@example.org)"})
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    titles = []
    for item in data.get("items", []):
        if item.get("type") != "image":
            continue
        title = item.get("title") or ""
        if _nama_valid_untuk_panorama(title):
            titles.append(title)

    return _cek_resolusi_dan_pilih(titles, lang=lang)


def fallback_gambar_wilayah(w):
    """Gambar panorama alam lokal berdasarkan karakteristik geografis wilayah."""
    if w.k7 >= 4.2 or w.k5 < 120:
        return static("pemeringkatan/images/pltb-wind.jpg")
    return static("pemeringkatan/images/plts-solar.jpg")


def dapatkan_gambar_lanskap(w):
    """Mengembalikan URL foto panorama alam beresolusi tinggi dari DB, atau mencari & menyimpannya."""
    if w.gambar_lanskap and _nama_valid_untuk_panorama(w.gambar_lanskap):
        return w.gambar_lanskap

    nama = w.kabkota.strip()
    kandidat_judul = [nama]
    if not nama.lower().startswith(("kota ", "kabupaten ")):
        kandidat_judul.append(f"Kabupaten {nama}")
    kandidat_judul.append(w.provinsi)

    deadline = time.monotonic() + 4.5
    for judul in kandidat_judul:
        if time.monotonic() >= deadline:
            break
        url = _cari_media_wikipedia(judul, "id")
        if not url and time.monotonic() < deadline:
            url = _cari_media_wikipedia(judul, "en")
        if url:
            w.gambar_lanskap = url
            try:
                w.save(update_fields=["gambar_lanskap"])
            except DatabaseError:
                pass
            return url

    return fallback_gambar_wilayah(w)
