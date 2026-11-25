from django.db import models

from .services.kriteria import KRITERIA


class Wilayah(models.Model):
    kode_bps = models.CharField(max_length=10, unique=True)
    kabkota = models.CharField("Kabupaten/Kota", max_length=100)
    provinsi = models.CharField(max_length=100, db_index=True)
    jenis = models.CharField("Jenis wilayah", max_length=30, blank=True)

    # 10 kriteria (nilai mentah, urutan sama dengan KRITERIA)
    k1 = models.FloatField("Populasi")
    k2 = models.FloatField("Kebutuhan Listrik")
    k3 = models.FloatField("IPM")
    k4 = models.FloatField("Jarak ke jalan arteri")
    k5 = models.FloatField("Variasi elevasi")
    k6 = models.FloatField("Radiasi surya")
    k7 = models.FloatField("Kecepatan angin 100 m")
    k8 = models.FloatField("Lahan tersedia")
    k9 = models.FloatField("Tutupan pohon")
    k10 = models.FloatField("Ekosistem sensitif")

    # hasil resmi (bobot AHP penelitian)
    v_topsis = models.FloatField(null=True, blank=True)
    peringkat_topsis = models.PositiveIntegerField(null=True, blank=True)
    net_flow = models.FloatField(null=True, blank=True)
    peringkat_promethee = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    gambar_lanskap = models.CharField("URL gambar lanskap", max_length=500, blank=True, default="")

    class Meta:
        ordering = ["peringkat_promethee", "kabkota"]
        verbose_name = "Wilayah"
        verbose_name_plural = "Wilayah"

    def __str__(self):
        return f"{self.kabkota} ({self.provinsi})"

    def nilai_mentah(self):
        return [getattr(self, k["field"]) for k in KRITERIA]
