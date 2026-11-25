"""Definisi 10 kriteria dan pembobotan AHP (bagian 1-3 notebook)."""
from functools import lru_cache

import numpy as np

# field   : nama field di model Wilayah
# kolom   : nama kolom di CSV
# log     : True -> transformasi log(1+x) saat praproses
# level   : tingkat kepentingan 1-9 untuk membentuk matriks perbandingan berpasangan AHP
KRITERIA = [
    dict(kode="K-1", field="k1", kolom="C01_populasi_2024", nama="Populasi",
         aspek="Sosial ekonomi", atribut="benefit", log=True, level=3, satuan="jiwa"),
    dict(kode="K-2", field="k2", kolom="C02_ntl_radiance_mean", nama="Kebutuhan Listrik",
         aspek="Sosial ekonomi", atribut="benefit", log=True, level=3, satuan=""),
    dict(kode="K-3", field="k3", kolom="C03_ipm_2024", nama="IPM",
         aspek="Sosial ekonomi", atribut="benefit", log=False, level=2, satuan=""),
    dict(kode="K-4", field="k4", kolom="C04_dist_to_primary_trunk_km", nama="Jarak ke jalan arteri",
         aspek="Sumber daya", atribut="cost", log=True, level=4, satuan="km"),
    dict(kode="K-5", field="k5", kolom="C05_elevation_std_m", nama="Variasi elevasi",
         aspek="Sumber daya", atribut="cost", log=False, level=3, satuan="m"),
    dict(kode="K-6", field="k6", kolom="C06_allsky_sfc_sw_dwn_mean", nama="Radiasi surya",
         aspek="Sumber daya", atribut="benefit", log=False, level=6, satuan=""),
    dict(kode="K-7", field="k7", kolom="C07_wind_speed_100m_mean_ms", nama="Kecepatan angin 100 m",
         aspek="Sumber daya", atribut="benefit", log=False, level=5, satuan="m/s"),
    dict(kode="K-8", field="k8", kolom="C08_pct_lahan_tersedia", nama="Lahan tersedia",
         aspek="Sumber daya", atribut="benefit", log=True, level=5, satuan="%"),
    dict(kode="K-9", field="k9", kolom="C09_pct_tree_cover", nama="Tutupan pohon",
         aspek="Lingkungan", atribut="cost", log=False, level=2, satuan="%"),
    dict(kode="K-10", field="k10", kolom="C10_pct_ekosistem_sensitif", nama="Ekosistem sensitif",
         aspek="Lingkungan", atribut="cost", log=True, level=4, satuan="%"),
]

JUMLAH = len(KRITERIA)
BENEFIT = np.array([k["atribut"] == "benefit" for k in KRITERIA])
FIELDS = [k["field"] for k in KRITERIA]
RI_N10 = 1.49  # Random Index untuk n = 10


def matriks_ahp(level=None):
    """Matriks perbandingan berpasangan dari selisih tingkat kepentingan (skala 1-9)."""
    level = [k["level"] for k in KRITERIA] if level is None else level
    n = len(level)
    A = np.ones((n, n))
    for i in range(n):
        for j in range(n):
            d = level[i] - level[j]
            A[i, j] = min(1 + d, 9) if d >= 0 else 1 / min(1 - d, 9)
    return A


@lru_cache(maxsize=1)
def _ahp():
    A = matriks_ahp()
    n = len(A)
    w = (A / A.sum(axis=0)).mean(axis=1)
    lam = ((A @ w) / w).mean()
    ci = (lam - n) / (n - 1)
    return tuple(w), float(ci / RI_N10)


def bobot_resmi():
    """Bobot AHP hasil penelitian (jumlah = 1)."""
    return np.array(_ahp()[0])


def cr_resmi():
    """Consistency Ratio dari matriks AHP resmi."""
    return _ahp()[1]
