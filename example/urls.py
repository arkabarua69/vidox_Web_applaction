from django.urls import path
from example import views

app_name = "downloader"

urlpatterns = [
    path("", views.index_view, name="index"),  # your homepage view
    path("about/", views.about_view, name="about"),
    path("contact/", views.contact_view, name="contact"),
    path("download/video", views.download_video, name="download_video"),
    path("download/audio", views.download_audio, name="download_audio"),
]
