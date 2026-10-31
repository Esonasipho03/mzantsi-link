"""
Database-backed file storage for uploaded photos.

Why: Render's free web service has a throwaway filesystem, so every
redeploy deletes uploaded photos. The database survives redeploys, so
in production (MEDIA_IN_DB=1) photos are stored there instead, and
served back by `serve_media` at the same /media/... URLs the templates
already use. Locally the normal FileSystemStorage is still used.

Large phone photos are shrunk on the way in (longest side 1600px,
JPEG) so a free database isn't filled by a handful of 8 MB uploads.
"""
import mimetypes
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.http import Http404, HttpResponse
from django.utils.deconstruct import deconstructible
from PIL import Image

MAX_SIDE = 1600


def _shrink_if_image(name, data):
    """Return (bytes, content_type). Non-images pass through untouched."""
    guessed = mimetypes.guess_type(name)[0] or "application/octet-stream"
    if not guessed.startswith("image/"):
        return data, guessed
    try:
        img = Image.open(BytesIO(data))
        if max(img.size) <= MAX_SIDE and len(data) <= 700_000:
            return data, guessed
        img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        out = BytesIO()
        img.save(out, format="JPEG", quality=85)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return data, guessed


@deconstructible
class DatabaseStorage(Storage):
    def _model(self):
        from accounts.models import StoredFile  # lazy: avoids import cycle at startup
        return StoredFile

    def _open(self, name, mode="rb"):
        try:
            row = self._model().objects.get(name=name)
        except self._model().DoesNotExist:
            raise FileNotFoundError(name)
        return ContentFile(bytes(row.content), name=name)

    def _save(self, name, content):
        data, content_type = _shrink_if_image(name, content.read())
        self._model().objects.create(name=name, content=data, content_type=content_type)
        return name

    def exists(self, name):
        return self._model().objects.filter(name=name).exists()

    def delete(self, name):
        self._model().objects.filter(name=name).delete()

    def size(self, name):
        return len(self._open(name).read())

    def url(self, name):
        from django.conf import settings
        return settings.MEDIA_URL + name.lstrip("/")


def serve_media(request, path):
    """GET /media/<path> straight from the database."""
    from accounts.models import StoredFile
    try:
        row = StoredFile.objects.get(name=path)
    except StoredFile.DoesNotExist:
        raise Http404
    response = HttpResponse(bytes(row.content), content_type=row.content_type)
    response["Cache-Control"] = "public, max-age=86400"
    return response
