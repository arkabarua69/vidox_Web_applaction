# downloader/views.py
import os
import tempfile
import shutil
import uuid
import mimetypes
from django.shortcuts import render, redirect
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest
from django.urls import reverse
from django.contrib import messages

# Optional import for contact form
try:
    from .forms import ContactForm

    FORMS_AVAILABLE = True
except ImportError:
    FORMS_AVAILABLE = False

# yt_dlp import
try:
    from yt_dlp import YoutubeDL

    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False


def index_view(request):
    return render(request, "downloader/index.html")


def _download_with_ytdlp(url, opts_extra=None, cookies_path=None):
    """
    Core function to download video/audio using yt_dlp
    """
    if not YTDLP_AVAILABLE:
        raise Exception("yt_dlp module is not available in this environment.")

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

        # Optional cookies for age-restricted videos
        if cookies_path:
            ydl_opts["cookiefile"] = cookies_path

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)

        return tmpdir, filepath, info

    except Exception as e:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
        raise e


def download_video(request):
    """
    Download video view
    """
    url = request.GET.get("url") or request.POST.get("url")
    quality = request.GET.get("quality") or request.POST.get("quality") or "best"

    if not url:
        return HttpResponseBadRequest("Missing 'url' parameter.")

    # Prevent SSRF / local file access
    lower = url.lower()
    if url.startswith("file://") or "127.0.0.1" in lower or "localhost" in lower:
        return HttpResponseBadRequest("Invalid URL.")

    extra = {}
    if quality != "best" and quality.endswith("p"):
        try:
            requested = int(quality[:-1])
            extra["format"] = (
                f"bestvideo[height<={requested}]+bestaudio/best[height<={requested}]/best"
            )
        except Exception:
            extra["format"] = "best"
    else:
        extra["format"] = "best"

    # Optional: path to cookies.txt for restricted videos
    cookies_path = None
    # cookies_path = "/path/to/cookies.txt"  # Uncomment if needed

    try:
        tmpdir, filepath, info = _download_with_ytdlp(
            url, opts_extra=extra, cookies_path=cookies_path
        )
    except Exception as e:
        return HttpResponse(f"Error downloading video: {e}", status=400)

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
        return response
    except Exception as e:
        return HttpResponse(f"Error streaming file: {e}", status=500)


def download_audio(request):
    """
    Download audio view
    """
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

    cookies_path = None  # Optional: path to cookies.txt

    try:
        tmpdir, filepath, info = _download_with_ytdlp(
            url, opts_extra=extra, cookies_path=cookies_path
        )
    except Exception as e:
        return HttpResponse(f"Error downloading audio: {e}", status=400)

    if not os.path.exists(filepath):
        try:
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
    if not FORMS_AVAILABLE:
        return HttpResponse("Contact form not available.", status=503)

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you — your message has been received.")
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
