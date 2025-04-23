import re
import os
import math
import tempfile
from typing import List, Dict, Optional
from moviepy.editor import TextClip, ImageClip, VideoFileClip, CompositeVideoClip
from PIL import Image, ImageFilter
import matplotlib.font_manager as fm
import numpy as np
import openai
import json
from dotenv import load_dotenv

load_dotenv()
from config import CAPTION_SETTINGS, BASE_DIR  # import caption settings

api_key = os.getenv("OPENAI_API_KEY")

# Function to extract audio from video
def extract_audio(input_video_path: str) -> str:
    try:
        video = VideoFileClip(input_video_path)
        audio = video.audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
            audio.write_audiofile(temp_audio_file.name, codec='pcm_s16le')
            return temp_audio_file.name
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return ""

# Function to transcribe audio using Whisper
def transcribe_audio_whisper(audio_file_path: str) -> Dict:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

    try:
        with open(audio_file_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                file=audio_file,
                model="whisper-1",
                response_format="verbose_json"  # Ensure this returns detailed segment info
            )
        return response
    except Exception as e:
        print(f"Error transcribing audio with Whisper: {e}")
        return {}

# Function to process Whisper transcription into captions
def generate_captions_from_whisper(transcription: Dict) -> List[Dict]:
    captions = []
    if not transcription or 'segments' not in transcription:
        print("No transcription segments found.")
        return captions

    for segment in transcription['segments']:
        captions.append({
            "start": segment['start'],
            "end": segment['end'],
            "text": segment['text'].strip()
        })

    return captions

# Function to get default font

def get_default_font() -> str:
    """Return the font path specified in CAPTION_SETTINGS or fall back."""
    font_path = CAPTION_SETTINGS.get("FONT", "Bangers-Regular.ttf")
    font_path = str((BASE_DIR / font_path).resolve()) if not os.path.isabs(font_path) else font_path
    if os.path.isfile(font_path):
        return font_path
    # fallback to DejaVu Sans
    import matplotlib.font_manager as fm
    return fm.findfont("DejaVu Sans")

    # fallback to DejaVu Sans
    import matplotlib.font_manager as fm
    fallback = fm.findfont("DejaVu Sans")
    if os.path.isfile(fallback):
        return fallback
    raise FileNotFoundError(f"Font file not found: {font_path}")

# Function to check if text fits within the video width (handles multi-line)
def does_text_fit(text: str, fontsize: int, font: str, max_width: int) -> bool:
    try:
        # Create a TextClip with 'caption' method to allow multi-line
        txt_clip = TextClip(
            txt=text,
            fontsize=fontsize,
            font=font,
            method='caption',
            size=(max_width, None),  # Width fixed, height auto
            align='center'
        )
        return txt_clip.w <= max_width
    except Exception as e:
        print(f"Error creating TextClip for fitting: {e}")
        return False

# Function to split a word if it's too long
def split_long_word(word: str, max_length: int = 15) -> List[str]:
    if len(word) <= max_length:
        return [word]
    
    split_words = []
    current_word = word
    while len(current_word) > max_length:
        part = current_word[:max_length] + '-'
        split_words.append(part)
        current_word = current_word[max_length:]
    split_words.append(current_word)
    return split_words

# Function to convert MoviePy clip to PIL Image
def moviepy_to_pillow(clip) -> Image.Image:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as temp_file:
        clip.save_frame(temp_file.name)
        image = Image.open(temp_file.name).convert("RGBA")
    return image

# Main function to add captions to video
def add_captions_to_video(
    input_video_path: str,
    transcription: List[Dict],
    output_video_path: str,
    font_path: Optional[str] = None,
    fontsize: int = CAPTION_SETTINGS.get('TEXT_SIZE',24),
    color: str = CAPTION_SETTINGS.get('COLOR','white'),
    stroke_color: str = CAPTION_SETTINGS.get('STROKE_COLOR','black'),
    stroke_width: int = CAPTION_SETTINGS.get('STROKE_WIDTH',2),
    position: tuple = ('center', CAPTION_SETTINGS.get('CAPTION_POSITION', ('center', 1240))[1]),
    blur_radius: int = 0,
    opacity: float = 1.0,
    bg_color: str = 'transparent',
    max_words_per_caption: int = 8,  # Adjusted as per user request
    time_scale: float = 1.0,
    start_delay: float = 0.0,
    duration_adjust: float = 0.0,
    per_caption_offset: Optional[Dict[int, float]] = None
):
    # Load the video
    try:
        video = VideoFileClip(input_video_path)
    except Exception as e:
        print(f"Error loading video file: {e}")
        return

    # Use default font if not provided
    if font_path is None:
        try:
            font_path = get_default_font()
        except FileNotFoundError as e:
            print(e)
            return

    # Check if the font file exists
    if not os.path.isfile(font_path):
        print(f"Font file not found at {font_path}. Please provide a valid font file.")
        return

    # Define maximum width for captions (90% of video width)
    max_caption_width = int(video.w * CAPTION_SETTINGS.get('SUBTITLE_MAX_WIDTH', 0.8))

    # Convert transcription segments to word-level list
    words_list = []
    for idx, segment in enumerate(transcription):
        text = segment['text']
        start = segment['start'] * time_scale + start_delay + (per_caption_offset.get(idx, 0) if per_caption_offset else 0)
        end = segment['end'] * time_scale + start_delay + duration_adjust + (per_caption_offset.get(idx, 0) if per_caption_offset else 0)
        words = text.split()
        n_words = len(words)
        if n_words == 0:
            continue
        duration = (end - start) / n_words if n_words > 0 else 0

        for i, word in enumerate(words):
            word_start = start + i * duration
            word_end = word_start + duration
            words_list.append({
                "word": word,
                "start": word_start,
                "end": word_end
            })

    # Initialize variables for caption grouping
    captions = []
    current_caption = []
    current_start = None
    current_end = None

    for idx, word_info in enumerate(words_list):
        word = word_info["word"]
        word_start = word_info["start"]
        word_end = word_info["end"]

        # Add word to current caption
        if not current_caption:
            current_start = word_start

        current_caption.append(word)
        current_end = word_end

        # Check if we've reached max words per caption
        if len(current_caption) >= max_words_per_caption:
            captions.append({
                "start": current_start,
                "end": current_end,
                "text": " ".join(current_caption)
            })
            current_caption = []
            current_start = None
            current_end = None

    # Add any remaining caption
    if current_caption:
        captions.append({
            "start": current_start,
            "end": current_end,
            "text": " ".join(current_caption)
        })

    # Process captions to handle multi-line text
    processed_captions = []
    for idx, caption in enumerate(captions):
        text = caption["text"]
        start = caption["start"]
        end = caption["end"]

        lines = []
        words = text.split()
        current_line = ""

        for word in words:
            tentative_line = f"{current_line} {word}".strip()
            # Check if adding the word keeps the line within width
            if does_text_fit(tentative_line, fontsize, font_path, max_caption_width):
                current_line = tentative_line
            else:
                if current_line:
                    lines.append(current_line)
                # Check if the single word fits
                if does_text_fit(word, fontsize, font_path, max_caption_width):
                    current_line = word
                else:
                    # Split the long word
                    split_words = split_long_word(word)
                    for split_word in split_words:
                        if does_text_fit(split_word, fontsize, font_path, max_caption_width):
                            lines.append(split_word)
                        else:
                            print(f"Word '{split_word}' is too long to fit even on a new line. Skipping.")
                    current_line = ""
        if current_line:
            lines.append(current_line)

        # Combine lines with line breaks
        multi_line_text = "\n".join(lines)
        processed_captions.append({
            "start": start,
            "end": end,
            "text": multi_line_text
        })

    # Create TextClips for all captions
    text_clips = []
    for idx, caption in enumerate(processed_captions):
        text = caption["text"]
        start = caption["start"]
        duration = caption["end"] - caption["start"]

        # Create the TextClip with multi-line support
        try:
            txt_clip = TextClip(
                txt=text,
                fontsize=fontsize,
                color=color,
                font=font_path,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                method='caption',  # Use 'caption' to handle multi-line text
                size=(max_caption_width, None),  # Width fixed, height auto
                align='center'  # Center align the text
            )
        except Exception as e:
            print(f"Error creating TextClip for caption '{text}': {e}")
            continue

        # Apply opacity if needed
        if opacity < 1.0:
            txt_clip = txt_clip.set_opacity(opacity)

        # Apply blur if needed
        if blur_radius > 0:
            try:
                pil_img = moviepy_to_pillow(txt_clip)
                pil_img_blurred = pil_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                blurred_array = np.array(pil_img_blurred)
                txt_clip = ImageClip(blurred_array).set_duration(duration)
            except Exception as e:
                print(f"Error applying blur to caption '{text}': {e}")

        # Position the caption
        txt_clip = txt_clip.set_position(position).set_start(start).set_duration(duration)

        text_clips.append(txt_clip)

    # Overlay all TextClips on the video
    final_video = CompositeVideoClip([video] + text_clips)

    # Write the final video to the output path
    try:
        final_video.write_videofile(output_video_path, codec="libx264", audio_codec="aac")
    except Exception as e:
        print(f"Error writing output video: {e}")

# Example usage
if __name__ == "__main__":
    input_video = "input_video.mp4"                # Path to your input video
    output_video = "output_with_captions.mp4"      # Desired output video path

    # Define timing adjustments
    time_scale = 1.0            # 1.0 = no change, >1.0 = slower captions, <1.0 = faster
    start_delay = 0.0           # Seconds to delay all captions
    duration_adjust = 0.0       # Seconds to adjust duration of each caption
    per_caption_offset = {      # Optional: {caption_index: offset_in_seconds}
        # Example:
        # 2: -0.5,  # Shift the third caption 0.5 seconds earlier
        # 5: 1.0    # Shift the sixth caption 1 second later
    }

    # Get a default font path
    try:
        font_path = "Bangers-Regular.ttf"  # Ensure this font file exists or provide another
        if not os.path.isfile(font_path):
            print(f"Font file '{font_path}' not found. Using default font.")
            font_path = None
    except FileNotFoundError as e:
        print(e)
        font_path = None

    # Extract audio from video
    audio_path = extract_audio(input_video)
    if not audio_path:
        print("Failed to extract audio. Exiting.")
        exit(1)

    # Transcribe audio using Whisper
    transcription_response = transcribe_audio_whisper(audio_path)
    if not transcription_response:
        print("Transcription failed. Exiting.")
        exit(1)

    # Generate captions from transcription
    captions = generate_captions_from_whisper(transcription_response)
    if not captions:
        print("No captions generated from transcription. Exiting.")
        exit(1)

    # Clean up the temporary audio file
    try:
        os.remove(audio_path)
    except Exception as e:
        print(f"Error removing temporary audio file: {e}")

    # Add captions to video
    add_captions_to_video(
        input_video_path=input_video,
        transcription=captions,
        output_video_path=output_video,
        font_path=font_path,          # Using the specified font or default
        fontsize=90,                  # Adjust as needed
        color="white",
        stroke_color="black",
        stroke_width=2,
        position=(40, 1150),
        blur_radius=0,                # Adjust blur as needed
        opacity=1.0,
        bg_color='transparent',
        max_words_per_caption=8,     # Set to desired value (e.g., 12)
        time_scale=time_scale,        # Set according to your needs
        start_delay=start_delay,      # Set according to your needs
        duration_adjust=duration_adjust,  # Set according to your needs
        per_caption_offset=per_caption_offset  # Optional
    )