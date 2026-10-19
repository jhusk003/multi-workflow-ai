"""Server-generated, per-character audio. No silent/mismatched browser TTS substitution."""
from __future__ import annotations
import asyncio
import base64
import io
import json
import re
import urllib.error
import urllib.request
import wave

# Voices are deliberately explicit for each assistant, especially Alex.
GOOGLE_VOICES = {'Morgan':'Aoede','Jordan':'Puck','Taylor':'Charon','Alex':'Kore'}
ELEVEN_FEMALE = {'Morgan':'EXAVITQu4vr4xnSDxMaL','Alex':'EXAVITQu4vr4xnSDxMaL'}


def _plain_text(value: str) -> str:
    s = re.sub(r'(?m)^\s*[-*]\s+', '', value or '')
    s = re.sub(r'[`*_#>|]+', ' ', s)
    return ' '.join(s.split())[:850]


def edge_mp3(text: str, voice: str, *, deadline: float=18) -> bytes:
    import edge_tts
    async def fetch():
        stream = edge_tts.Communicate(text, voice)
        result = bytearray()
        async for item in stream.stream():
            if item.get('type') == 'audio':
                result.extend(item.get('data') or b'')
        return bytes(result)
    return asyncio.run(asyncio.wait_for(fetch(), timeout=deadline))


def _wav_from_pcm(pcm: bytes, rate: int=24000) -> bytes:
    out=io.BytesIO()
    with wave.open(out, 'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(pcm)
    return out.getvalue()


def google_voice(text: str, name: str, key: str, model: str='gemini-2.5-flash-preview-tts', *, timeout: float=24):
    """Official generateContent TTS; output is audio/l16 or WAV."""
    voice=GOOGLE_VOICES.get(name, 'Kore')
    payload={'contents':[{'parts':[{'text':text}]}], 'generationConfig':{
        'responseModalities':['AUDIO'], 'speechConfig':{'voiceConfig':{'prebuiltVoiceConfig':{'voiceName':voice}}}}}
    url='https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent'
    req=urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type':'application/json','x-goog-api-key':key}, method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as response:
        body=json.load(response)
    for candidate in body.get('candidates',[]):
        for part in candidate.get('content',{}).get('parts',[]):
            inline=part.get('inlineData') or part.get('inline_data') or {}
            if inline.get('data'):
                raw=base64.b64decode(inline['data']); mime=str(inline.get('mimeType') or inline.get('mime_type') or '').lower()
                if raw[:4]==b'RIFF':return raw, 'audio/wav'
                if 'l16' in mime or 'pcm' in mime or 'audio' in mime:
                    match=re.search(r'rate=(\d+)',mime)
                    return _wav_from_pcm(raw,int(match.group(1)) if match else 24000), 'audio/wav'
    raise ValueError('Google returned no speech audio.')


def eleven_mp3(text: str, name: str, key: str, voice_id: str) -> bytes:
    # Do not use an unverified gender-mismatched default ID for Alex.
    if name in ELEVEN_FEMALE: voice_id=ELEVEN_FEMALE[name]
    if not voice_id:raise ValueError('No voice selected for ElevenLabs.')
    req=urllib.request.Request('https://api.elevenlabs.io/v1/text-to-speech/'+voice_id,
        data=json.dumps({'text':text,'model_id':'eleven_multilingual_v2'}).encode(),
        headers={'xi-api-key':key,'Content-Type':'application/json','Accept':'audio/mpeg'},method='POST')
    with urllib.request.urlopen(req,timeout=18) as response:return response.read()


def synthesize(text: str, assistant: dict, get_secret):
    """Return base64 audio, MIME type, provider, concise error. Never emit fake audio."""
    clean=_plain_text(text)
    if not clean:return '', '', '', 'Nothing to read aloud.'
    notes=[]; name=assistant.get('name','Alex')
    voice=assistant.get('voice','en-US-JennyNeural')
    try:
        audio=edge_mp3(clean,voice)
        if len(audio)>300:return base64.b64encode(audio).decode('ascii'),'audio/mpeg',f'Edge TTS · {voice}',''
        notes.append('Edge TTS produced no audio')
    except ImportError:
        notes.append('Edge TTS package missing')
    except Exception as error:
        notes.append('Edge TTS: '+type(error).__name__)
    key=get_secret('GEMINI_API_KEY') or get_secret('GOOGLE_API_KEY')
    if key:
        model=(get_secret('SELLER_TTS_MODEL') or 'gemini-2.5-flash-preview-tts').strip()
        if not re.fullmatch(r'[A-Za-z0-9._-]+',model):model='gemini-2.5-flash-preview-tts'
        try:
            audio,mime=google_voice(clean,name,key,model)
            if len(audio)>300:return base64.b64encode(audio).decode('ascii'),mime,f'Google TTS · {model} · {GOOGLE_VOICES.get(name)}',''
            notes.append('Google speech returned no audio')
        except urllib.error.HTTPError as error:
            notes.append(f'Google TTS HTTP {error.code}')
        except Exception as error:
            notes.append('Google TTS: '+type(error).__name__)
    else:notes.append('Google speech key missing')
    eleven_key=get_secret('ELEVENLABS_API_KEY')
    if eleven_key:
        try:
            raw=eleven_mp3(clean,name,eleven_key,assistant.get('eleven_voice_id',''))
            if len(raw)>300:return base64.b64encode(raw).decode('ascii'),'audio/mpeg','ElevenLabs',''
            notes.append('ElevenLabs produced no audio')
        except Exception as error:notes.append('ElevenLabs: '+type(error).__name__)
    # Never put API keys, returned payloads or text into the error string.
    return '', '', '', ' / '.join(notes)+'. Try Regenerate voice, or review Render logs and provider access.'
