import os
import json
from pathlib import Path

from scripts import generate_video_script
from visuals import (
    get_model_config_by_style,
    generate_image,
    poll_generation_status,
    extract_image_url,
    download_content,
)
from tts import process_tts
from video_assembler import assemble_video
import captions
from overlay import add_text_overlay
from config import VISUALS_DIR, VIDEO_SCRIPTS_DIR, FINAL_VIDEO_DIR

# Ensure required directories exist
for directory in [VISUALS_DIR, VIDEO_SCRIPTS_DIR, FINAL_VIDEO_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


def get_user_input():
    """Interactive prompts for basic video parameters."""
    topic = input("Enter video topic: ").strip()
    size = input("Enter video size (e.g., 1080x1920) [1080x1920]: ").strip() or "1080x1920"
    length = int(input("Enter total video length in seconds: "))
    num_sections = int(input("Enter number of sections: "))
    num_segments = int(input("Enter number of segments per section: "))
    return topic, size, length, num_sections, num_segments


def generate_and_download_images(script, model_style="Leonardo Phoenix"):
    """Iterates over script segments, generates images, downloads them, and injects local paths."""
    model_config = get_model_config_by_style(model_style)
    for section in script["sections"]:
        for segment in section["segments"]:
            prompt = segment["visual"]["prompt"]
            generation_id = generate_image(prompt, model_config)
            if not generation_id:
                raise RuntimeError(f"Failed to start image generation for prompt: {prompt}")
            data = poll_generation_status(generation_id)
            if not data:
                raise RuntimeError("Image generation did not complete.")
            image_url = extract_image_url(data)
            if not image_url:
                raise RuntimeError("Could not extract image URL.")
            # Local image path
            img_filename = f"section_{section['section_number']}_segment_{segment['segment_number']}.png"
            img_path = VISUALS_DIR / img_filename
            download_content(image_url, str(img_path))
            segment["visual"]["image_path"] = str(img_path)
    return script


def create_captions(video_path):
    """Run Whisper via capwhisp helper to create caption list."""
    audio_temp = captions.extract_audio(video_path)
    transcription = captions.transcribe_audio_whisper(audio_temp)
    cap_list = captions.generate_captions_from_whisper(transcription)
    # Clean up temp audio
    try:
        if audio_temp and Path(audio_temp).exists():
            Path(audio_temp).unlink()
    except Exception:
        pass
    return cap_list


def main():
    topic, size, length, num_sections, num_segments = get_user_input()

    # 1. Generate initial video script
    script = generate_video_script(topic, length, size, num_sections, num_segments)
    if not script:
        print("Error generating video script.")
        return

    # 2. Generate & download visuals
    script = generate_and_download_images(script)

    # 3. Generate narration TTS & update script
    script = process_tts(script)

    # 4. Persist enriched script to disk
    script_json_path = VIDEO_SCRIPTS_DIR / f"{topic.replace(' ','_')}_script.json"
    with open(script_json_path, "w") as f:
        json.dump(script, f, indent=4)
    print(f"Script saved to {script_json_path}")

    # 5. Assemble video (returns path to raw video)
    raw_video_path = Path(assemble_video(str(script_json_path))).resolve()
    if not raw_video_path.exists():
        print(f"assemble_video did not produce expected file at {raw_video_path} – aborting.")
        return
    print(f"Raw video created at {raw_video_path}")

    
    
    # 6. Captioning (write to new file to avoid in-place overwrite issues)
    captioned_video_path = raw_video_path.with_name(raw_video_path.stem + "_cap.mp4")
    caption_list = create_captions(str(raw_video_path))
    if caption_list:
        try:
            captions.add_captions_to_video(
                input_video_path=str(raw_video_path),
                    transcription=caption_list,
                output_video_path=str(captioned_video_path)
            )
        except Exception as e:
            print(f"Captioning failed: {e}")
    else:
        print("Warning: No captions generated; skipping caption overlay.")

    # If captioned file wasn't created, fall back to raw
    if not captioned_video_path.exists():
        captioned_video_path = raw_video_path
# 7. Header / footer overlay
    final_output_path = FINAL_VIDEO_DIR / f"{topic.replace(' ','_')}_final.mp4"
    add_text_overlay(
        input_video_path=str(captioned_video_path),
        output_video_path=str(final_output_path),
        start_text="Comment Below: Your Idea Could Be Next!",
        end_text="Want to see your idea here? Comment Below!",
        start_duration=5,
        end_duration=5,
        start_font_path="Bangers-Regular.ttf",
        end_font_path="Bangers-Regular.ttf",
        start_fontsize=75,
        end_fontsize=75,
        start_position=(20, 300),
        end_position=(20, 1500),
        text_color="white",
        bg_color=(0, 0, 0),
        col_opacity=0.3,
        padding=5,
        fade_in=True,
        fade_out=True,
        fade_duration=1,
    )

    print(f"Video processing complete! Final video saved at {final_output_path}")


if __name__ == "__main__":
    main()