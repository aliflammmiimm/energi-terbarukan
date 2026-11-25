from django.contrib import admin
from django.templatetags.static import static
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url=static("pemeringkatan/images/favicon.svg"), permanent=True)),
    path("admin/", admin.site.urls),
    path("", include("pemeringkatan.urls")),
]
