"""TOPSIS dan PROMETHEE II (bagian 2 dan 4 notebook). Murni numpy, tanpa dependensi Django/SciPy."""
import numpy as np

from .kriteria import BENEFIT, KRITERIA

Q_FAKTOR = 0.5   # ambang indiferen  q = 0,5 x simpangan baku
P_FAKTOR = 2.0   # ambang preferensi p = 2,0 x simpangan baku


def _rank_array(arr, method="min"):
    """Menghitung peringkat 1-based menggunakan numpy murni (mendukung method='min' dan 'average')."""
    values = np.asarray(arr, dtype=float)
    if values.size == 0:
        return np.array([], dtype=int if method == "min" else float)
    _, inv, counts = np.unique(values, return_inverse=True, return_counts=True)
    starts = np.cumsum(counts) - counts + 1
    if method == "average":
        ranks = starts + (counts - 1) / 2.0
        return ranks[inv]
    return starts[inv].astype(int)


def praproses(nilai):
    """Transformasi log(1+x) pada kriteria yang sangat miring. nilai: (alternatif x 10)."""
    X = np.array(nilai, dtype=float)
    for j, k in enumerate(KRITERIA):
        if k["log"]:
            X[:, j] = np.log1p(X[:, j])
    return X


def peringkat(skor):
    """Peringkat 1 = skor tertinggi (seri mendapat peringkat terkecil)."""
    return _rank_array(-np.asarray(skor, dtype=float), method="min")


def korelasi_spearman(x, y):
    """Korelasi peringkat Spearman (rho) menggunakan numpy murni."""
    rx = _rank_array(x, method="average")
    ry = _rank_array(y, method="average")
    if rx.size <= 2 or rx.size != ry.size:
        return None
    dx = rx - rx.mean()
    dy = ry - ry.mean()
    denom = float(np.sqrt((dx * dx).sum() * (dy * dy).sum()))
    if denom == 0.0:
        return None
    return float((dx * dy).sum() / denom)


def topsis(Xd, w):
    R = Xd / np.sqrt((Xd ** 2).sum(axis=0))
    V = R * w
    ideal_pos = np.where(BENEFIT, V.max(axis=0), V.min(axis=0))
    ideal_neg = np.where(BENEFIT, V.min(axis=0), V.max(axis=0))
    dp = np.sqrt(((V - ideal_pos) ** 2).sum(axis=1))
    dn = np.sqrt(((V - ideal_neg) ** 2).sum(axis=1))
    return dn / (dp + dn)


def promethee(Xd, w):
    """PROMETHEE II, fungsi preferensi linear. Mengembalikan net flow."""
    m = len(Xd)
    sd = Xd.std(axis=0, ddof=1)
    q, p = Q_FAKTOR * sd, P_FAKTOR * sd
    rentang = np.where(p - q == 0, 1.0, p - q)       # hindari bagi nol bila sd = 0
    Xb = np.where(BENEFIT, Xd, -Xd)                   # kriteria cost dibalik
    pi = np.zeros((m, m))
    for j in range(Xd.shape[1]):
        selisih = Xb[:, j][:, None] - Xb[:, j][None, :]
        pi += w[j] * np.clip((selisih - q[j]) / rentang[j], 0, 1)
    fplus = pi.sum(axis=1) / (m - 1)
    fmin = pi.sum(axis=0) / (m - 1)
    return fplus - fmin
