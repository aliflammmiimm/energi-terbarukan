from django.urls import path

from . import views

app_name = "pemeringkatan"

urlpatterns = [
    path("", views.beranda, name="beranda"),                                   # 1. Beranda
    path("peringkat/", views.peringkat_resmi, name="peringkat"),               # 2. Pemeringkatan resmi
    path("wilayah/<str:kode>/", views.detail_wilayah, name="detail"),          # 3. Detail wilayah
    path("simulasi/", views.simulasi, name="simulasi"),                        # 4-6. Atur bobot, seimbangkan, jalankan
    path("simulasi/hasil/", views.hasil_simulasi, name="hasil"),               # 8. Hasil simulasi
    path("evaluasi/", views.evaluasi, name="evaluasi"),                        # Evaluasi 0-7
    path("api/wilayah-peta/", views.api_wilayah_peta, name="api_wilayah_peta"),
]
