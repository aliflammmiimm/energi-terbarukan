"""Pemuatan hasil evaluasi 0-7 dari output tersimpan notebook kodeprogram1.ipynb."""
import json
import math
from pathlib import Path

EVALUASI_JSON = Path(__file__).resolve().parent.parent / "data" / "evaluasi_0_7.json"


def _tentukan_unggulan(vt, vp, arah):
    if math.isclose(vt, vp, abs_tol=1e-12):
        return "Setara", "setara"
    if arah == "min":
        return ("AHP-TOPSIS", "topsis") if vt < vp else ("AHP-PROMETHEE II", "promethee")
    if arah == "max":
        return ("AHP-TOPSIS", "topsis") if vt > vp else ("AHP-PROMETHEE II", "promethee")
    lebih_besar = "AHP-TOPSIS" if vt > vp else "AHP-PROMETHEE II"
    return f"Penyebaran lebih besar: {lebih_besar}", "spread"


def _penjelasan_dimensi(row, unggul):
    no = row["no"]
    vt = row["ahp_topsis"]
    vp = row["ahp_promethee"]
    if no == 0:
        return f"Pada uji sensitivitas OAT, {unggul} mencatat pergeseran peringkat rata-rata (MARS) lebih kecil ({min(vt, vp):.5f} vs {max(vt, vp):.5f})."
    if no == 1:
        return f"Pada uji OAT, {unggul} mempertahankan irisan Top-10 lebih tinggi ({max(vt, vp):.2f}% vs {min(vt, vp):.2f}%)."
    if no == 2:
        return f"Pada 1.000 skenario Monte Carlo, {unggul} lebih stabil dengan MARS lebih rendah ({min(vt, vp):.5f} vs {max(vt, vp):.5f})."
    if no == 3:
        return f"Pada simulasi Monte Carlo, {unggul} mempertahankan wilayah Top-10 lebih konsisten ({max(vt, vp):.2f}% vs {min(vt, vp):.2f}%)."
    if no == 4:
        return f"AHP-PROMETHEE II ({vp:.5f}) memiliki simpangan baku skor ternormalisasi lebih besar dibanding AHP-TOPSIS ({vt:.5f}), menunjukkan sebaran skor lebih lebar dan bukan ukuran akurasi tunggal."
    if no == 5:
        return f"Pada uji leave-one-out, {unggul} menghasilkan rasio pembalikan peringkat (RR) lebih rendah ({min(vt, vp):.5f} vs {max(vt, vp):.5f})."
    if no == 6:
        return f"Pada penghapusan 10% alternatif secara acak, {unggul} mencatat RR lebih rendah ({min(vt, vp):.5f} vs {max(vt, vp):.5f})."
    return f"Dari sisi kecepatan eksekusi pemeringkatan, {unggul} jauh lebih singkat ({min(vt, vp):.5f} detik vs {max(vt, vp):.5f} detik)."


def muat_evaluasi_0_7():
    """Membaca 8 dimensi evaluasi (0-7) dari JSON hasil eksekusi notebook tanpa menghitung ulang."""
    if not EVALUASI_JSON.exists():
        return {"sumber": "", "baris": [], "ringkasan": {}}

    data = json.loads(EVALUASI_JSON.read_text(encoding="utf-8"))
    baris = []
    unggul_prom = 0
    unggul_topsis = 0

    for r in data.get("evaluasi", []):
        vt = float(r["ahp_topsis"])
        vp = float(r["ahp_promethee"])
        unggul, kode_unggul = _tentukan_unggulan(vt, vp, r["arah"])
        if kode_unggul == "promethee":
            unggul_prom += 1
        elif kode_unggul == "topsis":
            unggul_topsis += 1

        maks = max(vt, vp)
        pct_t = round(vt / maks * 100, 1) if maks > 0 else 0.0
        pct_p = round(vp / maks * 100, 1) if maks > 0 else 0.0
        is_pct = r["no"] in (1, 3)
        baris.append({
            "no": r["no"],
            "dimensi": r["dimensi"],
            "kriteria": r["kriteria"],
            "arah": r["arah"],
            "ahp_topsis": vt,
            "ahp_promethee": vp,
            "fmt_topsis": f"{vt:.2f}%" if is_pct else f"{vt:.5f}",
            "fmt_promethee": f"{vp:.2f}%" if is_pct else f"{vp:.5f}",
            "pct_topsis": pct_t,
            "pct_promethee": pct_p,
            "unggul": unggul,
            "kode_unggul": kode_unggul,
            "penjelasan": _penjelasan_dimensi(r, unggul),
        })

    return {
        "sumber": data.get("sumber", "kodeprogram1.ipynb"),
        "baris": baris,
        "ringkasan": {
            "total_dimensi": len(baris),
            "unggul_promethee": unggul_prom,
            "unggul_topsis": unggul_topsis,
        },
    }

