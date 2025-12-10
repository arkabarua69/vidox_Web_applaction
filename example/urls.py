from django.urls import path
from example import views
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

app_name = "downloader"

urlpatterns = [
    path("", views.index_view, name="index"),  # your homepage view
    path("about/", views.about_view, name="about"),
    path("contact/", views.contact_view, name="contact"),
    path("download/video", views.download_video, name="download_video"),
    path("download/audio", views.download_audio, name="download_audio"),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
