import datetime
import sqlite3
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from pemeringkatan.models import Wilayah

WILAYAH_FIELDS = (
    "kabkota",
    "provinsi",
    "jenis",
    "k1",
    "k2",
    "k3",
    "k4",
    "k5",
    "k6",
    "k7",
    "k8",
    "k9",
    "k10",
    "v_topsis",
    "peringkat_topsis",
    "net_flow",
    "peringkat_promethee",
    "gambar_lanskap",
)


def _parse_utc_dt(value):
    if not value:
        return None
    dt = parse_datetime(value)
    if dt is not None and timezone.is_naive(dt):
        return timezone.make_aware(dt, datetime.timezone.utc)
    return dt


def baca_sqlite(sqlite_path):
    """Membaca seluruh baris Wilayah dan auth_user dari file SQLite sumber."""
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        wilayah_rows = [dict(r) for r in conn.execute("SELECT * FROM pemeringkatan_wilayah ORDER BY kode_bps")]
        user_rows = [dict(r) for r in conn.execute("SELECT * FROM auth_user ORDER BY id")]
    finally:
        conn.close()
    return wilayah_rows, user_rows


class Command(BaseCommand):
    help = "Salin seluruh data Wilayah (termasuk skor & gambar_lanskap) dan akun admin dari db.sqlite3 ke database aktif (PostgreSQL)."

    def add_arguments(self, parser):
        parser.add_argument("sqlite_path", nargs="?", default="db.sqlite3")

    def handle(self, *args, **opts):
        sqlite_path = Path(opts["sqlite_path"]).resolve()
        if not sqlite_path.exists():
            raise CommandError(f"File SQLite tidak ditemukan: {sqlite_path}")

        db_conf = settings.DATABASES["default"]
        if db_conf["ENGINE"] == "django.db.backends.sqlite3" and Path(db_conf["NAME"]).resolve() == sqlite_path:
            raise CommandError("Database aktif masih menunjuk ke db.sqlite3 yang sama. Set DATABASE_URL ke PostgreSQL terlebih dahulu.")

        wilayah_rows, user_rows = baca_sqlite(sqlite_path)
        if not wilayah_rows:
            raise CommandError("Tabel pemeringkatan_wilayah di SQLite kosong.")

        User = get_user_model()
        with transaction.atomic():
            for row in wilayah_rows:
                defaults = {f: row[f] for f in WILAYAH_FIELDS}
                Wilayah.objects.update_or_create(kode_bps=row["kode_bps"], defaults=defaults)

            for u in user_rows:
                User.objects.update_or_create(
                    username=u["username"],
                    defaults={
                        "password": u["password"],
                        "email": u["email"] or "",
                        "first_name": u["first_name"] or "",
                        "last_name": u["last_name"] or "",
                        "is_superuser": bool(u["is_superuser"]),
                        "is_staff": bool(u["is_staff"]),
                        "is_active": bool(u["is_active"]),
                        "last_login": _parse_utc_dt(u["last_login"]),
                        "date_joined": _parse_utc_dt(u["date_joined"]) or timezone.now(),
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Berhasil menyalin {len(wilayah_rows)} wilayah dan {len(user_rows)} pengguna ke database aktif."
            )
        )
