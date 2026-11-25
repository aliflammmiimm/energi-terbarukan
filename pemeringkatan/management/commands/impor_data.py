import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pemeringkatan.models import Wilayah
from pemeringkatan.services.data import hitung_resmi
from pemeringkatan.services.kriteria import KRITERIA


class Command(BaseCommand):
    help = "Impor data_kriteria_kabkota.csv lalu hitung peringkat resmi (AHP + TOPSIS + PROMETHEE II)."

    def add_arguments(self, parser):
        parser.add_argument("csv", nargs="?", default="data/data_kriteria_kabkota.csv")

    def handle(self, *args, **opts):
        path = Path(opts["csv"])
        if not path.exists():
            raise CommandError(f"File tidak ditemukan: {path}")

        with path.open(encoding="utf-8-sig", newline="") as f:
            baris = list(csv.DictReader(f))
        if not baris:
            raise CommandError("CSV kosong.")

        wajib = ["bps_kabkota_code", "kabkota_name", "prov_name"] + [k["kolom"] for k in KRITERIA]
        hilang = [c for c in wajib if c not in baris[0]]
        if hilang:
            raise CommandError(f"Kolom tidak ada di CSV: {', '.join(hilang)}")

        with transaction.atomic():
            for r in baris:
                nilai = {k["field"]: float(r[k["kolom"]]) for k in KRITERIA}
                Wilayah.objects.update_or_create(
                    kode_bps=r["bps_kabkota_code"].strip(),
                    defaults=dict(kabkota=r["kabkota_name"].strip(),
                                  provinsi=r["prov_name"].strip(),
                                  jenis=(r.get("jenis_wilayah") or "").strip(),
                                  **nilai))
            n = hitung_resmi()
        self.stdout.write(self.style.SUCCESS(f"{n} wilayah diimpor dan peringkat resmi dihitung."))
