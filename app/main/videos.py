import os
import re
import time
import uuid
from flask import current_app

ALLOWED_VIDEO_EXTENSIONS = (".mp4", ".mov")
_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
PENDING_MAX_AGE = 24 * 60 * 60  # seconds
FINAL_NAME_RE = re.compile(r"^[0-9]+-[0-9a-f]{32}\.(mp4|mov)$")


def _dir(name):
    path = os.path.join(current_app.config["VIDEO_UPLOAD_DIR"], name)
    os.makedirs(path, exist_ok=True)
    return path


def final_dir():
    return _dir("videos")


def _find_pending(user_id, token):
    """Return the pending file path for this user's token, or None."""
    if not isinstance(token, str) or not _TOKEN_RE.match(token):
        return None
    for ext in ALLOWED_VIDEO_EXTENSIONS:
        path = os.path.join(_dir("pending"), f"{int(user_id)}-{token}{ext}")
        if os.path.isfile(path):
            return path
    return None


def save_pending(user_id, file_storage):
    """Store an upload in the user's pending area; return its token."""
    ext = os.path.splitext(file_storage.filename or "")[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return None
    _purge_pending(user_id)
    token = uuid.uuid4().hex
    file_storage.save(os.path.join(_dir("pending"), f"{int(user_id)}-{token}{ext}"))
    return token


def _purge_pending(user_id):
    """Keep at most one pending upload per user and expire stale ones."""
    pending = _dir("pending")
    cutoff = time.time() - PENDING_MAX_AGE
    for name in os.listdir(pending):
        path = os.path.join(pending, name)
        try:
            if name.startswith(f"{int(user_id)}-") or os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


def delete_pending(user_id, token):
    path = _find_pending(user_id, token)
    if path is None:
        return False
    os.remove(path)
    return True


def promote(user_id, token):
    """Move a finished pending upload to final storage; return its filename."""
    path = _find_pending(user_id, token)
    if path is None:
        return None
    filename = os.path.basename(path)
    os.replace(path, os.path.join(final_dir(), filename))
    return filename


def unpromote(filename):
    """Move a promoted file back to pending (used when publishing fails)."""
    os.replace(
        os.path.join(final_dir(), filename), os.path.join(_dir("pending"), filename)
    )


def has_pending(user_id, token):
    return _find_pending(user_id, token) is not None


def format_size(num_bytes):
    if num_bytes >= 1024 * 1024:
        return f"{round(num_bytes / (1024 * 1024))} MB"
    return f"{max(1, round(num_bytes / 1024))} KB"
