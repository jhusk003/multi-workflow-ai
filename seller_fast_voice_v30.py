"""Generate speech without holding up the visible AI reply. Main thread owns session state."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, Future
import threading
import uuid

from seller_voice_v29 import synthesize

_EXECUTOR = ThreadPoolExecutor(max_workers=3, thread_name_prefix='seller-voice')
_PENDING: dict[str, Future] = {}
_LOCK = threading.Lock()
_KEYS = ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'ELEVENLABS_API_KEY', 'SELLER_TTS_MODEL')


def schedule(workspace, response, assistant, secret):
    """Called on Streamlit script thread; collect secrets here, not on worker."""
    old = workspace.pop('_sa_v30_voice_token', None)
    if old:
        with _LOCK:
            previous = _PENDING.pop(old, None)
        if previous:
            previous.cancel()
    keys = {key: secret(key) for key in _KEYS}
    token = uuid.uuid4().hex
    if not workspace.get('reply_id'):
        workspace['reply_id'] = uuid.uuid4().hex
    workspace['_sa_v30_voice_token'] = token
    workspace['_sa_v30_voice_reply'] = workspace['reply_id']
    for key in ('last_audio', 'last_audio_mime', 'last_audio_provider', 'last_audio_error'):
        workspace[key] = ''
    future = _EXECUTOR.submit(synthesize, str(response), dict(assistant), keys.get)
    with _LOCK:
        _PENDING[token] = future
    return token


def is_pending(workspace):
    return bool(workspace.get('_sa_v30_voice_token'))


def collect(workspace):
    """Called by Streamlit fragment; does not block while the voice is being made."""
    token = workspace.get('_sa_v30_voice_token')
    if not token:
        return False
    with _LOCK:
        future = _PENDING.get(token)
    if future is not None and not future.done():
        return False
    with _LOCK:
        future = _PENDING.pop(token, None)
    workspace.pop('_sa_v30_voice_token', None)
    message_id = workspace.pop('_sa_v30_voice_reply', None)
    if message_id != workspace.get('reply_id'):
        return False  # Outdated result must never play for a newer reply.
    if future is None:
        result = ('', '', '', 'Voice worker was interrupted. Use Regenerate voice.')
    else:
        try:
            result = future.result()  # Already done; never blocks here.
        except Exception:
            result = ('', '', '', 'Voice generation stopped. Use Regenerate voice.')
    audio, mime, provider, error = result
    workspace['last_audio'] = audio
    workspace['last_audio_mime'] = mime
    workspace['last_audio_provider'] = provider
    workspace['last_audio_error'] = error
    return True
