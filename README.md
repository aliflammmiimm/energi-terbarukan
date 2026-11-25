# Pemeringkatan Wilayah (Django)

Sistem pemeringkatan 514 Kabupaten/Kota: AHP (bobot) + PROMETHEE II (utama) + TOPSIS (pembanding).

## Menjalankan

```bash
pip install -r requirements.txt
cp /path/ke/data_kriteria_kabkota.csv data/
python manage.py makemigrations pemeringkatan
python manage.py migrate
python manage.py impor_data data/data_kriteria_kabkota.csv   # impor + hitung peringkat resmi
python manage.py runserver
```

## Halaman

| URL | Alur |
|---|---|
| `/` | 1. Beranda |
| `/peringkat/` | 2. Pemeringkatan resmi (cari, filter provinsi, urut, paginasi) |
| `/wilayah/<kode_bps>/` | 3. Detail wilayah |
| `/simulasi/` | 4-7. Atur bobot, Seimbangkan Bobot, Jalankan Simulasi |
| `/simulasi/hasil/` | 8. Top 10, seluruh peringkat, perbandingan dengan resmi |

## Struktur

- `pemeringkatan/services/kriteria.py` : 10 kriteria, atribut benefit/cost, log1p, bobot AHP + CR
- `pemeringkatan/services/metode.py` : `praproses`, `topsis`, `promethee`, `peringkat` (dari notebook)
- `pemeringkatan/services/data.py` : `hitung_resmi()` dan `jalankan_simulasi()`
- `pemeringkatan/management/commands/impor_data.py` : impor CSV

Peringkat resmi disimpan di database saat impor. Simulasi dihitung per permintaan dan disimpan di session
pengguna (tanpa login), sehingga tidak mengubah hasil resmi.
