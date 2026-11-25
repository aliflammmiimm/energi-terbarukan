from django.contrib import admin

from .models import Wilayah


@admin.register(Wilayah)
class WilayahAdmin(admin.ModelAdmin):
    list_display = ("kabkota", "provinsi", "jenis", "peringkat_promethee", "peringkat_topsis")
    list_filter = ("provinsi", "jenis")
    search_fields = ("kabkota", "provinsi", "kode_bps")
