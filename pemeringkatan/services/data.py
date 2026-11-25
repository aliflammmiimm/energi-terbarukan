"""Pengambilan matriks keputusan, perhitungan hasil resmi, dan simulasi."""
import numpy as np

from ..models import Wilayah
from .kriteria import JUMLAH, bobot_resmi
from .metode import peringkat, praproses, promethee, topsis


def ambil_matriks():
    """Seluruh wilayah (urut kode BPS, tetap) dan matriks nilai mentahnya."""
    wilayah = list(Wilayah.objects.order_by("kode_bps"))
    nilai = np.array([w.nilai_mentah() for w in wilayah], dtype=float)
    return wilayah, nilai


def hitung_resmi():
    """Hitung ulang peringkat resmi (bobot AHP penelitian) dan simpan ke database."""
    wilayah, nilai = ambil_matriks()
    if len(wilayah) < 3:
        raise ValueError("Data wilayah belum cukup untuk dihitung.")
    X = praproses(nilai)
    w = bobot_resmi()
    v = topsis(X, w)
    phi = promethee(X, w)
    rt, rp = peringkat(v), peringkat(phi)
    for i, o in enumerate(wilayah):
        o.v_topsis, o.peringkat_topsis = float(v[i]), int(rt[i])
        o.net_flow, o.peringkat_promethee = float(phi[i]), int(rp[i])
    Wilayah.objects.bulk_update(
        wilayah, ["v_topsis", "peringkat_topsis", "net_flow", "peringkat_promethee"], batch_size=200)
    return len(wilayah)


def jalankan_simulasi(bobot_persen):
    """Hitung ulang seluruh wilayah dengan PROMETHEE II.

    bobot_persen: 10 angka (persen). Mengembalikan daftar [kode_bps, net_flow, peringkat].
    """
    wilayah, nilai = ambil_matriks()
    w = np.asarray(bobot_persen, dtype=float)
    if len(w) != JUMLAH or w.sum() <= 0:
        raise ValueError("Bobot tidak valid.")
    w = w / w.sum()
    phi = promethee(praproses(nilai), w)
    rank = peringkat(phi)
    return [[o.kode_bps, float(phi[i]), int(rank[i])] for i, o in enumerate(wilayah)]
