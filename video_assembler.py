import os
import json
import requests
import numpy as np
import random
from pathlib import Path
from PIL import Image
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, VideoFileClip
)
from moviepy.video.fx.all import fadein, fadeout
from moviepy.audio.fx.all import audio_loop, audio_fadein, audio_fadeout
from dotenv import load_dotenv
from config import VIDEO_SIZE, FPS, FINAL_VIDEO_DIR

# -------------------- PIL Compatibility --------------------
def ensure_pil_compat():
    try:
        Image.ANTIALIAS
    except AttributeError:
        Image.ANTIALIAS = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS
ensure_pil_compat()

# -------------------- Environment --------------------
load_dotenv()

# -------------------- Banned Songs List --------------------
# Populate with titles to exclude from background selection
BANNED_SONGS = [
    "Upbeat Piano and Trumpet for Joyful Moments",
    "Song Title B",
]

def is_banned(sound_info):
    """Return True if a sound's name matches a banned title."""
    return sound_info.get('name', '') in BANNED_SONGS

# -------------------- Configuration --------------------
API_KEY = os.getenv("FREESOUND_API_KEY")
if not API_KEY:
    raise ValueError("FREESOUND_API_KEY environment variable not set.")
BASE_URL = "https://freesound.org/apiv2"
OUTPUT_SOUNDS = Path("./sounds")
OUTPUT_SOUNDS.mkdir(exist_ok=True)
BACKGROUND_MUSIC_USER = "Nancy_Sinclair"

# Default transition parameters
DEFAULT_TRANSITION_VOLUME = 0.1
DEFAULT_TRANSITION_FADE_DURATION = 0.15
DEFAULT_TRANSITION_OFFSET = 0.1
DEFAULT_TRANSITION_SPEED = 1.0
ZOOM_PERCENT = 0.1
FALLBACK_QUERIES = [
    'uplifting', 'ambient', 'inspirational', 'calm',
    'soft piano', 'orchestral', 'neutral', 'chill'
]

# -------------------- Freesound Helpers --------------------
def search_any_sounds(query, filters=None, sort="rating_desc", num_results=50):
    """Search Freesound text search endpoint."""
    print(f"[VERBOSE] Searching sounds for '{query}' with filters '{filters}'")
    params = {
        "query": query,
        "filter": filters or '',
        "sort": sort,
        "fields": "id,name,previews,license,duration,username,tags,pack",
        "token": API_KEY,
        "page_size": num_results
    }
    try:
        r = requests.get(f"{BASE_URL}/search/text/", params=params)
        r.raise_for_status()
        results = r.json().get('results', [])
        print(f"[VERBOSE] Found {len(results)} sounds for '{query}'")
        return results
    except Exception as e:
        print(f"[ERROR] search_any_sounds: {e}")
        return []

def download_sound(sound_info, output_path):
    """Download preview MP3; cache locally."""
    if output_path.exists():
        print(f"[VERBOSE] Using cached: {output_path}")
        return str(output_path)
    previews = sound_info.get('previews')
    if not previews:
        detail = requests.get(f"{BASE_URL}/sounds/{sound_info['id']}/", params={'token': API_KEY})
        detail.raise_for_status()
        previews = detail.json().get('previews', {})
    url = previews.get('preview-hq-mp3') or previews.get('preview-lq-mp3')
    if not url:
        print(f"[ERROR] No preview URL for sound {sound_info.get('id')}")
        return None
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in resp.iter_content(1024):
            f.write(chunk)
    print(f"[VERBOSE] Downloaded: {sound_info.get('name')}")
    return str(output_path)

# -------------------- Background Music --------------------
def fetch_background_music(bg_setting, total_duration):
    """Pick a background track from Nancy_Sinclair only."""
    filters = f'username:"{BACKGROUND_MUSIC_USER}" AND tag:music'
    print(f"[VERBOSE] Nancy search for background '{bg_setting}' with filters '{filters}'")
    sounds = [s for s in search_any_sounds(bg_setting or '', filters) if not is_banned(s)]
    print(f"[VERBOSE] Nancy library returned {len(sounds)} results")
    if not sounds:
        print("[VERBOSE] No Nancy results, trying Nancy-only fallback queries")
        for q in FALLBACK_QUERIES:
            print(f"[VERBOSE] Nancy fallback query '{q}' with filters '{filters}'")
            candidates = [s for s in search_any_sounds(q, filters) if not is_banned(s)]
            print(f"[VERBOSE] Nancy fallback '{q}' returned {len(candidates)} results")
            if candidates:
                sounds = candidates
                break
    if not sounds:
        print("[ERROR] No background music found after Nancy fallback.")
        return None, None
    pick = sounds[0]
    print(f"[VERBOSE] Selected background track: {pick.get('name')}")
    path = OUTPUT_SOUNDS / f"bg_{pick['id']}.mp3"
    return download_sound(pick, path), pick.get('name')

# -------------------- Transitions --------------------
def fetch_transition(effect_name):
    """Pick a transition sound (global search)."""
    query = effect_name or 'transition'
    print(f"[VERBOSE] Searching transitions for '{query}' with filter 'tag:transition'")
    results = [s for s in search_any_sounds(query, 'tag:transition') if not is_banned(s)]
    print(f"[VERBOSE] Found {len(results)} transition sounds for '{query}'")
    if not results:
        print(f"[ERROR] No transition sounds found for '{query}', skipping.")
        return None
    pick = results[0]
    print(f"[VERBOSE] Selected transition sound: {pick.get('name')}")
    path = OUTPUT_SOUNDS / f"tr_{pick['id']}.mp3"
    return download_sound(pick, path)

# -------------------- Zoom Effect --------------------
def zoom_effect(clip):
    dur = clip.duration
    def fl(get_frame, t):
        factor = 1 + ZOOM_PERCENT * (t/(dur/2) if t < dur/2 else (dur-t)/(dur/2))
        frame = get_frame(t)
        img = Image.fromarray(frame)
        resample = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS
        sz = img.resize((int(frame.shape[1]*factor), int(frame.shape[0]*factor)), resample)
        return np.array(sz)
    return clip.fl(fl, apply_to=['video'])

# -------------------- Assemble Video --------------------
def assemble_video(script_json_path):
    jp = Path(script_json_path).resolve()
    print(f"[VERBOSE] Loading script: {jp}")
    data = json.loads(jp.read_text())
    settings = data.get('settings', {})
    use_trans = settings.get('use_transitions', False)
    use_bg = settings.get('use_background_music', False)
    bg_setting = data.get('background_music', '')
    sections = data.get('sections', [])

    # override or defaults
    bg_volume = settings.get('bg_music_volume', 0.1)
    tv = settings.get('transition_volume', DEFAULT_TRANSITION_VOLUME)
    tf = settings.get('transition_fade_duration', DEFAULT_TRANSITION_FADE_DURATION)
    to = settings.get('transition_offset', DEFAULT_TRANSITION_OFFSET)

    clips, narrs, trans_auds = [], [], []
    timeline = 0.0

    # build clips
    for sec in sections:
        for seg in sec.get('segments', []):
            narr_info = seg['narration']
            ap = narr_info.get('audio_path')
            dur = narr_info.get('duration', 0)
            if ap and os.path.exists(ap):
                ac = AudioFileClip(ap).set_start(timeline)
                narrs.append(ac)
                dur = ac.duration
            img_p = seg.get('visual', {}).get('image_path')
            if img_p and os.path.exists(img_p):
                ic = ImageClip(img_p).resize(VIDEO_SIZE).set_duration(dur)
                ic = zoom_effect(ic).fx(fadein, tf).fx(fadeout, tf).set_start(timeline)
                clips.append(ic)
            if use_trans:
                trp = fetch_transition(seg.get('sound', {}).get('transition_effect', ''))
                if trp:
                    ot = AudioFileClip(trp)
                    ta = ot.subclip(0, tf) if ot.duration >= tf else ot.fx(audio_loop, duration=tf)
                    ta = audio_fadeout(ta.volumex(tv), tf).set_start(timeline + dur - to)
                    trans_auds.append(ta)
            timeline += dur

    if not clips:
        print("[ERROR] No clips to assemble.")
        return

    # visuals
    video_no_bg = concatenate_videoclips(clips, method="compose")
    total_dur = video_no_bg.duration

    # audio composite
    audio_comp = CompositeAudioClip(narrs + trans_auds).set_duration(total_dur)
    raw_video = video_no_bg.set_audio(audio_comp)

    # write raw
    raw_path = Path(FINAL_VIDEO_DIR) / f"{jp.stem}_raw.mp4"
    print(f"[VERBOSE] Writing raw video: {raw_path}")
    raw_video.write_videofile(str(raw_path), fps=FPS, codec='libx264', audio_codec='aac')

    # final with bg
    final_path = Path(FINAL_VIDEO_DIR) / f"{jp.stem}.mp4"
    if use_bg:
        print("[VERBOSE] Applying background music...")
        bg_file, bg_name = fetch_background_music(bg_setting, total_dur)
        if bg_file:
            base = VideoFileClip(str(raw_path))
            bg_audio = AudioFileClip(bg_file)
            bg_audio = bg_audio.fx(audio_loop, duration=total_dur) if bg_audio.duration < total_dur else bg_audio.subclip(0, total_dur)
            bg_audio = bg_audio.volumex(bg_volume)
            combined = CompositeAudioClip([base.audio, bg_audio]).set_duration(total_dur)
            final_vid = base.set_audio(combined)
            print(f"[VERBOSE] Writing final video: {final_path}")
            final_vid.write_videofile(str(final_path), fps=FPS, codec='libx264', audio_codec='aac')
            data['background_music_name'] = bg_name
        else:
            raw_path.rename(final_path)
    else:
        raw_path.rename(final_path)

    # update JSON
    data['raw_video'] = str(raw_path)
    data['final_video'] = str(final_path)
    jp.write_text(json.dumps(data, indent=2), encoding='utf-8')
    print("[VERBOSE] Done. JSON updated.")
    return str(final_path)

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python video_creator.py <script.json>")
        sys.exit(1)
    assemble_video(sys.argv[1])
