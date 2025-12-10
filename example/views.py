import os
import tempfile
import shutil
import uuid
import mimetypes
from django.shortcuts import render, redirect
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest
from yt_dlp import YoutubeDL
from django.urls import reverse
from django.contrib import messages
from .forms import ContactForm


def index_view(request):
    return render(request, "downloader/index.html")


def _download_with_ytdlp(url, opts_extra=None):
    tmpdir = tempfile.mkdtemp(prefix="vidox_")
    try:
        outtmpl = os.path.join(tmpdir, "%(id)s.%(ext)s")
        ydl_opts = {
            "format": "best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "writethumbnail": False,
            "writesubtitles": False,
        }
        if opts_extra:
            ydl_opts.update(opts_extra)

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
        return tmpdir, filepath, info
    except Exception as e:
        # cleanup on failure
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
        raise


def download_video(request):
    url = request.GET.get("url") or request.POST.get("url")
    quality = request.GET.get("quality") or request.POST.get("quality") or "best"

    if not url:
        return HttpResponseBadRequest("Missing 'url' parameter.")

    # simple SSRF protection - reject file:// and private host hints
    lower = url.lower()
    if url.startswith("file://") or "127.0.0.1" in lower or "localhost" in lower:
        return HttpResponseBadRequest("Invalid URL.")

    extra = {}
    if quality and quality != "best" and quality.endswith("p"):
        try:
            requested = int(quality[:-1])
            extra["format"] = (
                f"bestvideo[height<={requested}]+bestaudio/best[height<={requested}]/best"
            )
        except Exception:
            extra["format"] = "best"
    else:
        extra["format"] = "best"

    try:
        tmpdir, filepath, info = _download_with_ytdlp(url, opts_extra=extra)
    except Exception as e:
        return HttpResponse(f"Error downloading: {e}", status=400)

    if not os.path.exists(filepath):
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
        return HttpResponse("Downloaded file not found.", status=500)

    title = info.get("title") or uuid.uuid4().hex
    ext = os.path.splitext(filepath)[1] or ".mp4"
    safe_name = f"{title}{ext}"

    try:
        response = FileResponse(
            open(filepath, "rb"), as_attachment=True, filename=safe_name
        )
        response["Content-Type"] = (
            mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        )
        # NOTE: we purposely don't delete tmpdir immediately to avoid breaking streaming.
        # Use management command to remove old vidox_* temp dirs.
        return response
    except Exception as e:
        return HttpResponse(f"Error streaming file: {e}", status=500)


def download_audio(request):
    url = request.GET.get("url") or request.POST.get("url")
    if not url:
        return HttpResponseBadRequest("Missing 'url' parameter.")

    extra = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    try:
        tmpdir, filepath, info = _download_with_ytdlp(url, opts_extra=extra)
    except Exception as e:
        return HttpResponse(f"Error downloading audio: {e}", status=400)

    if not os.path.exists(filepath):
        try:
            # try find any file inside tmpdir
            files = [
                f for f in os.listdir(tmpdir) if os.path.isfile(os.path.join(tmpdir, f))
            ]
            if files:
                filepath = os.path.join(tmpdir, files[0])
            else:
                shutil.rmtree(tmpdir)
                return HttpResponse("Converted file not found.", status=500)
        except Exception:
            pass

    title = info.get("title") or uuid.uuid4().hex
    ext = os.path.splitext(filepath)[1] or ".mp3"
    safe_name = f"{title}{ext}"

    try:
        response = FileResponse(
            open(filepath, "rb"), as_attachment=True, filename=safe_name
        )
        response["Content-Type"] = mimetypes.guess_type(safe_name)[0] or "audio/mpeg"
        return response
    except Exception as e:
        return HttpResponse(f"Error streaming audio: {e}", status=500)


def about_view(request):
    context = {
        "author_name": "Mac GunJon",
        "year": 2025,
        "social": {
            "facebook": "https://www.facebook.com/profile.php?id=61583639494248",
            "instagram": "https://www.instagram.com/mac_gunjon/",
            "youtube": "https://www.youtube.com/channel/UCoCsjO5rHKNRX9fcSVAJZ6Q",
            "discord": "https://discord.gg/yNRtTs468Q",
        },
    }
    return render(request, "downloader/about.html", context)


def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you — your message has been received.")
            # redirect to avoid duplicate POST
            return redirect(reverse("downloader:contact"))
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ContactForm()

    context = {
        "form": form,
        "author_name": "Mac GunJon",
        "year": 2025,
    }
    return render(request, "downloader/contact.html", context)
