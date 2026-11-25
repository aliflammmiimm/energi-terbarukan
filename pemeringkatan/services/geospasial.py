"""Layanan koordinat geografis kabupaten/kota dan rekomendasi energi terbarukan (PLTS/PLTB)."""
from bisect import bisect_left
import json
from functools import lru_cache
import math
from pathlib import Path

from django.urls import reverse

from .kriteria import KRITERIA

KOORDINAT_PATH = Path(__file__).resolve().parent.parent / "data" / "koordinat_kabkota.json"


@lru_cache(maxsize=1)
def _semua_koordinat():
    if not KOORDINAT_PATH.exists():
        return {}
    with open(KOORDINAT_PATH, encoding="utf-8") as f:
        return json.load(f)


def _koordinat_valid(lat, lng):
    if lat is None or lng is None:
        return False
    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        return False
    if not (math.isfinite(lat_f) and math.isfinite(lng_f)):
        return False
    if lat_f == 0.0 and lng_f == 0.0:
        return False
    return -11.5 <= lat_f <= 6.5 and 94.5 <= lng_f <= 141.5


def koordinat_wilayah(kode_bps):
    """Mengembalikan dict {lat, lng} untuk kode BPS tertentu jika valid berada di Indonesia."""
    item = _semua_koordinat().get(str(kode_bps))
    if not item:
        return None
    lat, lng = item.get("lat"), item.get("lng")
    if not _koordinat_valid(lat, lng):
        return None
    return {"lat": float(lat), "lng": float(lng)}


def _persentil_arrays():
    """Mengambil seluruh nilai k6 (surya) dan k7 (angin) dari database untuk perhitungan persentil."""
    from pemeringkatan.models import Wilayah

    rows = list(Wilayah.objects.values_list("k6", "k7"))
    surya = sorted(r[0] for r in rows)
    angin = sorted(r[1] for r in rows)
    return surya, angin


def _hitung_persentil(nilai, sorted_list):
    n = len(sorted_list)
    if n <= 1:
        return 50.0
    lebih_kecil = bisect_left(sorted_list, nilai)
    return round(lebih_kecil / (n - 1) * 100, 1)


def rekomendasi_energi(w, sorted_surya=None, sorted_angin=None):
    """Menentukan rekomendasi PLTS / PLTB berdasarkan perbandingan persentil kriteria surya (k6) dan angin (k7)."""
    if sorted_surya is None or sorted_angin is None:
        sorted_surya, sorted_angin = _persentil_arrays()

    p_surya = _hitung_persentil(w.k6, sorted_surya)
    p_angin = _hitung_persentil(w.k7, sorted_angin)
    selisih = p_surya - p_angin

    skor_str = f"{w.net_flow:.4f}" if w.net_flow is not None else "-"
    if selisih >= 8.0:
        kode = "PLTS"
        judul = "PLTS — Pembangkit Listrik Tenaga Surya"
        ringkas = "PLTS"
        alasan = (
            f"Berdasarkan data aktual kriteria, {w.kabkota} memiliki radiasi surya sebesar "
            f"{w.k6:.2f} W/m² (lebih tinggi dari {p_surya:.1f}% wilayah Indonesia), sedangkan "
            f"kecepatan angin pada ketinggian 100 m sebesar {w.k7:.2f} m/s (persentil {p_angin:.1f}%). "
            f"Dengan skor kelayakan akhir {skor_str}, pengembangan PLTS lebih direkomendasikan."
        )
    elif selisih <= -8.0:
        kode = "PLTB"
        judul = "PLTB — Pembangkit Listrik Tenaga Bayu"
        ringkas = "PLTB"
        alasan = (
            f"Berdasarkan data aktual kriteria, {w.kabkota} memiliki kecepatan angin pada ketinggian 100 m "
            f"sebesar {w.k7:.2f} m/s (lebih tinggi dari {p_angin:.1f}% wilayah Indonesia), melampaui "
            f"posisi relatif radiasi surya sebesar {w.k6:.2f} W/m² (persentil {p_surya:.1f}%). "
            f"Dengan skor kelayakan akhir {skor_str}, pengembangan PLTB menjadi alternatif utama."
        )
    else:
        kode = "HYBRID"
        judul = "Kombinasi PLTS dan PLTB"
        ringkas = "PLTS & PLTB"
        alasan = (
            f"Potensi energi surya ({w.k6:.2f} W/m², persentil {p_surya:.1f}%) dan kecepatan angin 100 m "
            f"({w.k7:.2f} m/s, persentil {p_angin:.1f}%) di {w.kabkota} berada pada tingkat yang berimbang. "
            f"Dengan skor kelayakan akhir {skor_str}, kombinasi PLTS maupun PLTB sama-sama layak dipertimbangkan."
        )

    return {
        "kode": kode,
        "judul": judul,
        "ringkas": ringkas,
        "alasan": alasan,
        "persentil_surya": p_surya,
        "persentil_angin": p_angin,
        "nilai_surya": round(w.k6, 2),
        "nilai_angin": round(w.k7, 2),
    }


def ringkasan_karakteristik(w, rek):
    """Menyusun ringkasan karakteristik geografis & sosial-ekonomi dari nilai aktual database."""
    jenis_label = w.jenis if w.jenis else "Wilayah administratif"
    return (
        f"{jenis_label} di Provinsi {w.provinsi} ini mencatat IPM {w.k3:.2f}, "
        f"ketersediaan lahan {w.k8:.2f}%, tutupan pohon {w.k9:.2f}%, serta "
        f"jarak rata-rata ke jalan arteri {w.k4:.2f} km. Potensi surya tercatat "
        f"{rek['nilai_surya']:.2f} W/m² dan kecepatan angin {rek['nilai_angin']:.2f} m/s."
    )


def deskripsi_geografis(w, rek):
    """Menyusun deskripsi Karakteristik Geografis dari data topografi dan tutupan lahan aktual."""
    if w.k5 is None or w.k8 is None or w.k9 is None:
        return "Informasi karakteristik geografis untuk wilayah ini belum tersedia dalam basis data."

    if w.k5 < 80:
        relief = f"bentang alam yang relatif datar hingga landai (variasi elevasi {w.k5:.1f} m)"
    elif w.k5 < 250:
        relief = f"bentang alam berombak hingga perbukitan (variasi elevasi {w.k5:.1f} m)"
    else:
        relief = f"bentang alam perbukitan terjal hingga pegunungan (variasi elevasi {w.k5:.1f} m)"

    jenis_label = w.jenis if w.jenis else "Wilayah"
    return (
        f"{jenis_label} {w.kabkota} di Provinsi {w.provinsi} memiliki {relief}, "
        f"dengan tutupan pohon sebesar {w.k9:.2f}%, proporsi lahan tersedia {w.k8:.2f}%, "
        f"serta proporsi ekosistem sensitif {w.k10:.2f}%. "
        f"Dari sisi aksesibilitas dan sumber daya alam, jarak rata-rata ke jaringan jalan arteri "
        f"tercatat {w.k4:.2f} km dengan radiasi surya {rek['nilai_surya']:.2f} W/m² dan "
        f"kecepatan angin pada ketinggian 100 m sebesar {rek['nilai_angin']:.2f} m/s sebagai "
        f"dasar pertimbangan kelayakan pengembangan {rek['ringkas']}."
    )


def data_peta_wilayah(wilayah_list):
    """Menghasilkan list dictionary serializable untuk marker peta Leaflet.js dari data aktual."""
    from pemeringkatan.models import Wilayah

    fields = [k["field"] for k in KRITERIA]
    all_rows = list(Wilayah.objects.values_list(*fields))
    sorted_cols = {
        k["field"]: sorted(row[idx] for row in all_rows)
        for idx, k in enumerate(KRITERIA)
    }
    sorted_surya = sorted_cols["k6"]
    sorted_angin = sorted_cols["k7"]
    total_n = len(all_rows)

    hasil = []
    for w in wilayah_list:
        koor = koordinat_wilayah(w.kode_bps)
        if not koor:
            continue
        rek = rekomendasi_energi(w, sorted_surya, sorted_angin)

        best_k = KRITERIA[0]["nama"]
        best_pct = -1.0
        for k in KRITERIA:
            val = getattr(w, k["field"])
            col = sorted_cols[k["field"]]
            if total_n > 1:
                if k["atribut"] == "benefit":
                    pct = bisect_left(col, val) / (total_n - 1) * 100
                else:
                    pct = (total_n - 1 - bisect_left(col, val)) / (total_n - 1) * 100
            else:
                pct = 50.0
            if pct > best_pct:
                best_pct = pct
                best_k = f"{k['kode']} {k['nama']} ({round(pct, 1)}%)"

        hasil.append({
            "kode": w.kode_bps,
            "kabkota": w.kabkota,
            "provinsi": w.provinsi,
            "peringkat": w.peringkat_promethee,
            "skor": round(w.net_flow, 4) if w.net_flow is not None else 0.0,
            "lat": koor["lat"],
            "lng": koor["lng"],
            "energi": rek["ringkas"],
            "energi_kode": rek["kode"],
            "energi_judul": rek["judul"],
            "kriteria_tertinggi": best_k,
            "k6": rek["nilai_surya"],
            "k7": rek["nilai_angin"],
            "url": reverse("pemeringkatan:detail", args=[w.kode_bps]),
        })
    return hasil
