import numpy as np
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Wilayah
from .services.data import jalankan_simulasi
from .services.evaluasi import muat_evaluasi_0_7
from .services.geospasial import (
    _persentil_arrays,
    data_peta_wilayah,
    deskripsi_geografis,
    koordinat_wilayah,
    rekomendasi_energi,
    ringkasan_karakteristik,
)
from .services.kriteria import KRITERIA, bobot_resmi, cr_resmi
from .services.lanskap import dapatkan_gambar_lanskap, fallback_gambar_wilayah
from .services.metode import korelasi_spearman

SESSION_BOBOT = "bobot_simulasi"      # 10 angka persen yang terakhir diisi pengguna
SESSION_HASIL = "hasil_simulasi"      # {"bobot": [...], "hasil": [[kode, net_flow, peringkat], ...]}
TOLERANSI_TOTAL = 0.01                # total bobot dianggap 100% bila selisih <= 0,01


def _bobot_resmi_persen():
    return [round(float(x) * 100, 2) for x in bobot_resmi()]


# ---------------------------------------------------------------- 1. Beranda
def beranda(request):
    qs = Wilayah.objects.all()
    total = qs.count()
    ctx = {"total": total}
    if total:
        top5 = list(qs.order_by("peringkat_promethee")[:5])
        surya_arr, angin_arr = _persentil_arrays()
        top5_cards = []
        for w in top5:
            rek = rekomendasi_energi(w, surya_arr, angin_arr)
            skor_bar = max(8, min(100, round(((w.net_flow or 0) + 1) / 2 * 100, 1)))
            top5_cards.append({
                "w": w,
                "rek": rek,
                "skor_bar": skor_bar,
                "koor": koordinat_wilayah(w.kode_bps),
            })
        ctx.update(
            jumlah_provinsi=qs.values("provinsi").distinct().count(),
            per_jenis=qs.exclude(jenis="").values("jenis").annotate(n=Count("id")).order_by("-n"),
            top5=top5,
            top5_cards=top5_cards,
            peta_wilayah=data_peta_wilayah(qs.order_by("peringkat_promethee")),
            rata_ipm=qs.aggregate(a=Avg("k3"))["a"],
            top_provinsi=qs.filter(peringkat_promethee__lte=20).values("provinsi")
                           .annotate(n=Count("id")).order_by("-n")[:5],
        )
    bobot = [dict(k, persen=p) for k, p in zip(KRITERIA, _bobot_resmi_persen())]
    ctx.update(bobot=bobot, cr=cr_resmi())
    return render(request, "pemeringkatan/beranda.html", ctx)


def api_wilayah_peta(request):
    """Endpoint JSON seluruh wilayah penelitian beserta koordinat dan rekomendasi energi."""
    q = request.GET.get("q", "").strip()
    qs = Wilayah.objects.order_by("peringkat_promethee")
    if q:
        qs = qs.filter(Q(kabkota__icontains=q) | Q(provinsi__icontains=q))
    items = data_peta_wilayah(qs)
    return JsonResponse({"total": len(items), "wilayah": items})


def evaluasi(request):
    """Halaman perbandingan hasil evaluasi 0-7 AHP-TOPSIS vs AHP-PROMETHEE II."""
    ctx = muat_evaluasi_0_7()
    return render(request, "pemeringkatan/evaluasi.html", ctx)


# ----------------------------------------------------- 2. Pemeringkatan resmi
URUTAN = {
    "promethee": "peringkat_promethee",
    "topsis": "peringkat_topsis",
    "nama": "kabkota",
    "provinsi": "provinsi",
}


def peringkat_resmi(request):
    q = request.GET.get("q", "").strip()
    prov = request.GET.get("provinsi", "").strip()
    urut = request.GET.get("urut", "promethee")
    if urut not in URUTAN:
        urut = "promethee"

    qs = Wilayah.objects.all()
    if q:
        qs = qs.filter(Q(kabkota__icontains=q) | Q(provinsi__icontains=q))
    if prov:
        qs = qs.filter(provinsi=prov)
    qs = qs.order_by(URUTAN[urut], "kabkota")

    halaman = Paginator(qs, 25).get_page(request.GET.get("page"))
    surya_arr, angin_arr = _persentil_arrays()
    for w in halaman.object_list:
        w.rekomendasi = rekomendasi_energi(w, surya_arr, angin_arr)
        w.koor = koordinat_wilayah(w.kode_bps)
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "pemeringkatan/peringkat.html", {
        "halaman": halaman,
        "peta_wilayah": data_peta_wilayah(halaman.object_list),
        "q": q, "prov": prov, "urut": urut,
        "daftar_provinsi": Wilayah.objects.order_by("provinsi").values_list("provinsi", flat=True).distinct(),
        "qs": params.urlencode(),
    })


# ------------------------------------------------------------ 3. Detail wilayah
def detail_wilayah(request, kode):
    w = get_object_or_404(Wilayah, kode_bps=kode)
    total = Wilayah.objects.count()
    bobot = _bobot_resmi_persen()
    baris = []
    for k, b in zip(KRITERIA, bobot):
        nilai = getattr(w, k["field"])
        # persentase wilayah lain yang lebih buruk pada kriteria ini (memperhatikan benefit/cost)
        lawan = {f"{k['field']}__lt": nilai} if k["atribut"] == "benefit" else {f"{k['field']}__gt": nilai}
        lebih_buruk = Wilayah.objects.filter(**lawan).count()
        baris.append(dict(k, nilai=nilai, bobot=b,
                          unggul=round(lebih_buruk / (total - 1) * 100, 1) if total > 1 else 0))
    rek = rekomendasi_energi(w)
    return render(request, "pemeringkatan/detail.html", {
        "w": w,
        "baris": baris,
        "total": total,
        "rekomendasi": rek,
        "karakteristik": ringkasan_karakteristik(w, rek),
        "deskripsi_geografis": deskripsi_geografis(w, rek),
        "gambar_lanskap": dapatkan_gambar_lanskap(w),
        "gambar_fallback": fallback_gambar_wilayah(w),
    })


# ---------------------------------------------------------------- 4-7. Simulasi
def _form_bobot(nilai, galat=None):
    galat = galat or {}
    return [dict(k, nilai=nilai[i], galat=galat.get(k["field"])) for i, k in enumerate(KRITERIA)]


def _baca_bobot(post):
    """Baca 10 input persen. Mengembalikan (nilai, galat per field)."""
    nilai, galat = [], {}
    for k in KRITERIA:
        mentah = post.get(k["field"], "").strip().replace(",", ".")
        try:
            v = float(mentah)
            if not np.isfinite(v) or v < 0:
                raise ValueError
        except ValueError:
            v = 0.0
            galat[k["field"]] = "Isi angka 0 atau lebih."
        nilai.append(v)
    return nilai, galat


def _seimbangkan(nilai):
    """Skala ulang agar total tepat 100% (2 desimal); sisa pembulatan masuk ke bobot terbesar."""
    arr = np.array(nilai, dtype=float)
    hasil = np.round(arr / arr.sum() * 100, 2)
    hasil[int(np.argmax(hasil))] += round(100 - hasil.sum(), 2)
    return [round(float(x), 2) for x in hasil]


@require_http_methods(["GET", "POST"])
def simulasi(request):
    if request.method == "GET":
        nilai = request.session.get(SESSION_BOBOT) or _bobot_resmi_persen()
        return render(request, "pemeringkatan/simulasi.html", {
            "form": _form_bobot(nilai),
            "total": round(sum(nilai), 2),
            "ada_hasil": bool(request.session.get(SESSION_HASIL)),
        })

    aksi = request.POST.get("aksi")
    if aksi == "reset":                                            # kembali ke kondisi awal
        request.session.pop(SESSION_BOBOT, None)
        request.session.pop(SESSION_HASIL, None)
        messages.info(request, "Pengaturan bobot dan area hasil simulasi dikembalikan ke kondisi awal.")
        return redirect("pemeringkatan:simulasi")

    nilai, galat = _baca_bobot(request.POST)
    total = round(sum(nilai), 2)
    request.session[SESSION_BOBOT] = nilai

    def tampil():
        return render(request, "pemeringkatan/simulasi.html",
                      {"form": _form_bobot(nilai, galat), "total": round(sum(nilai), 2)})

    if galat:
        messages.error(request, "Ada bobot yang tidak valid. Periksa kolom yang ditandai.")
        return tampil()

    if aksi == "seimbangkan":                                      # 6. Seimbangkan bobot
        if total <= 0:
            messages.error(request, "Total bobot 0%. Isi minimal satu bobot lebih dari 0.")
            return tampil()
        nilai = _seimbangkan(nilai)
        request.session[SESSION_BOBOT] = nilai
        messages.success(request, f"Bobot diseimbangkan: total sebelumnya {total:g}% menjadi 100%.")
        return tampil()

    # aksi == "jalankan"                                            # 7. Jalankan simulasi
    if abs(total - 100) > TOLERANSI_TOTAL:
        messages.error(request, f"Total bobot {total:g}%, harus 100%. Tekan “Seimbangkan Bobot”.")
        return tampil()
    if not Wilayah.objects.exists():
        messages.error(request, "Data wilayah belum diimpor.")
        return tampil()

    request.session[SESSION_HASIL] = {"bobot": nilai, "hasil": jalankan_simulasi(nilai)}
    return redirect("pemeringkatan:hasil")


# ------------------------------------------------------------ 8. Hasil simulasi
def hasil_simulasi(request):
    data = request.session.get(SESSION_HASIL)
    if not data:
        messages.info(request, "Belum ada hasil simulasi. Atur bobot lalu jalankan simulasi.")
        return redirect("pemeringkatan:simulasi")

    sim = {kode: (flow, rank) for kode, flow, rank in data["hasil"]}
    daftar = []
    for w in Wilayah.objects.all():
        if w.kode_bps not in sim:
            continue
        flow, rank = sim[w.kode_bps]
        daftar.append(dict(kode=w.kode_bps, kabkota=w.kabkota, provinsi=w.provinsi,
                           flow=flow, rank_sim=rank, rank_resmi=w.peringkat_promethee,
                           selisih=w.peringkat_promethee - rank))   # positif = naik dibanding resmi
    daftar.sort(key=lambda r: (r["rank_sim"], r["rank_resmi"]))

    rs = np.array([r["rank_sim"] for r in daftar])
    rr = np.array([r["rank_resmi"] for r in daftar])
    rho = korelasi_spearman(rs, rr)
    top_sim = {r["kode"] for r in daftar if r["rank_sim"] <= 10}
    top_resmi = {r["kode"] for r in daftar if r["rank_resmi"] <= 10}

    top10_resmi = sorted((r for r in daftar if r["rank_resmi"] <= 10), key=lambda r: r["rank_resmi"])
    bobot = [dict(k, resmi=r, simulasi=s, beda=round(s - r, 2))
             for k, r, s in zip(KRITERIA, _bobot_resmi_persen(), data["bobot"])]

    return render(request, "pemeringkatan/hasil.html", {
        "top10": daftar[:10],
        "top10_resmi": top10_resmi,
        "daftar": daftar,
        "bobot": bobot,
        "spearman": rho,
        "irisan_top10": len(top_sim & top_resmi),
        "rata_selisih": float(np.abs(rs - rr).mean()) if len(daftar) else 0,
        "naik": sum(1 for r in daftar if r["selisih"] > 0),
        "turun": sum(1 for r in daftar if r["selisih"] < 0),
        "sama": sum(1 for r in daftar if r["selisih"] == 0),
        "total": len(daftar),
    })
