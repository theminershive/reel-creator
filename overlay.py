from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import os
import sys

def list_available_fonts():
    """Lists available fonts for TextClip."""
    try:
        fonts = TextClip.list('font')
        print("Available Fonts:")
        for font in fonts:
            print(f" - {font}")
    except Exception as e:
        print(f"Error listing fonts: {e}")

def add_text_overlay(input_video_path, output_video_path,
                    start_text, end_text,
                    start_duration, end_duration,
                    start_font_path, end_font_path,
                    start_fontsize, end_fontsize,
                    start_position, end_position,
                    text_color, bg_color, col_opacity, padding,
                    fade_in=False, fade_out=False, fade_duration=1):
    """
    Adds start and end text overlays to a video.

    Parameters:
    - input_video_path: Path to the input video file.
    - output_video_path: Path to save the output video file.
    - start_text: Text to display at the start.
    - end_text: Text to display at the end.
    - start_duration: Duration in seconds for the start overlay.
    - end_duration: Duration in seconds for the end overlay.
    - start_font_path: Full path to the font file for the start text.
    - end_font_path: Full path to the font file for the end text.
    - start_fontsize: Font size for the start text.
    - end_fontsize: Font size for the end text.
    - start_position: Position tuple or string for the start overlay.
    - end_position: Position tuple or string for the end overlay.
    - text_color: Color of the text.
    - bg_color: Background color for the text box (as an RGB tuple).
    - col_opacity: Opacity of the background color (0 to 1).
    - padding: Padding around the text.
    - fade_in: Boolean to enable fade-in effect.
    - fade_out: Boolean to enable fade-out effect.
    - fade_duration: Duration of fade effects in seconds.
    """
    
    # Load the original video
    try:
        video = VideoFileClip(input_video_path)
    except Exception as e:
        print(f"Error loading video: {e}")
        sys.exit(1)
        
    video_width, video_height = video.size

    # Define a function to create a text clip with background
    def create_text_clip(text, duration, start_time, font_path, fontsize, position):
        # Create the text clip
        try:
            txt_clip = TextClip(txt=text,
                                fontsize=fontsize,
                                font=font_path,  # Use font file path
                                color=text_color,
                                method='caption',
                                size=(video_width - 40, None),
                                align='center')
        except Exception as e:
            print(f"Error creating TextClip with font '{font_path}': {e}")
            sys.exit(1)
        
        # Add background with specified opacity
        txt_bg = txt_clip.on_color(size=(txt_clip.w + 2*padding, txt_clip.h + 2*padding),
                                   color=bg_color,
                                   pos=(0,0),
                                   col_opacity=col_opacity)
        
        # Apply fade-in and fade-out if enabled
        if fade_in or fade_out:
            txt_bg = txt_bg.set_start(start_time).set_duration(duration)
            if fade_in:
                txt_bg = txt_bg.crossfadein(fade_duration)
            if fade_out:
                txt_bg = txt_bg.crossfadeout(fade_duration)
        else:
            txt_bg = txt_bg.set_start(start_time).set_duration(duration)
        
        # Position the text
        txt_bg = txt_bg.set_position(position)
        
        return txt_bg

    # Create start text clip
    start_clip = create_text_clip(
        text=start_text,
        duration=start_duration,
        start_time=0,
        font_path=start_font_path,
        fontsize=start_fontsize,
        position=start_position
    )

    # Create end text clip
    end_start_time = max(video.duration - end_duration, 0)
    end_clip = create_text_clip(
        text=end_text,
        duration=end_duration,
        start_time=end_start_time,
        font_path=end_font_path,
        fontsize=end_fontsize,
        position=end_position
    )

    # Composite the text clips over the original video
    final = CompositeVideoClip([video, start_clip, end_clip])

    # Write the result to a file
    try:
        final.write_videofile(output_video_path, codec='libx264', audio_codec='aac', threads=4, preset='medium')
    except Exception as e:
        print(f"Error writing video file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # ==================== CONFIGURATION OPTIONS ====================

    # ------------------ Text Contents ------------------
    START_TEXT = "Comment Below: Your Idea Could Be Next!"
    END_TEXT = "Want to see your idea here? Comment Below!"

    # ------------------ Durations (in seconds) ------------------
    START_DURATION = 5    # Duration for start overlay
    END_DURATION = 5      # Duration for end overlay

    # ------------------ Font Files ------------------
    # Specify the .ttf font files located in the same directory as this script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    START_FONT_FILE = "Bangers-Regular.ttf"          # Font file for start overlay
    END_FONT_FILE = "Bangers-Regular.ttf"            # Font file for end overlay

    # Full paths to the font files
    START_FONT_PATH = os.path.join(SCRIPT_DIR, START_FONT_FILE)
    END_FONT_PATH = os.path.join(SCRIPT_DIR, END_FONT_FILE)

    # ------------------ Font Sizes ------------------
    START_FONTSIZE = 75
    END_FONTSIZE = 75

    # ------------------ Positions ------------------
    # Can be a string like 'top', 'bottom', 'center', or a tuple (x, y)
    START_POSITION = (20, 300)      # Position for start overlay
    END_POSITION = (20, 1500)     # Position for end overlay

    # ------------------ Colors ------------------
    TEXT_COLOR = 'white'                     # Text color
    BG_COLOR = (0, 0, 0)                     # Background color as RGB tuple
    COL_OPACITY = .3                        # Background opacity (0 to 1)

    # ------------------ Padding ------------------
    PADDING = 5                             # Padding around text

    # ------------------ Animations ------------------
    FADE_IN = True                          # Enable fade-in for overlays
    FADE_OUT = True                         # Enable fade-out for overlays
    FADE_DURATION = 1                        # Duration of fade effects in seconds

    # ------------------ File Paths ------------------
    INPUT_VIDEO = "input_short.mp4"          # Path to your input video
    OUTPUT_VIDEO = "output_short_with_overlays.mp4"  # Desired output path

    # ============================================================

    # Optionally, list available fonts if needed
    # Uncomment the lines below to list available fonts and exit
    # list_available_fonts()
    # sys.exit()

    # Verify that font files exist
    if not os.path.isfile(START_FONT_PATH):
        print(f"Start font file '{START_FONT_FILE}' not found in '{SCRIPT_DIR}'.")
        sys.exit(1)
    if not os.path.isfile(END_FONT_PATH):
        print(f"End font file '{END_FONT_FILE}' not found in '{SCRIPT_DIR}'.")
        sys.exit(1)

    # Ensure the input file exists
    if not os.path.isfile(INPUT_VIDEO):
        print(f"Input video file '{INPUT_VIDEO}' not found.")
        sys.exit(1)
    else:
        add_text_overlay(
            input_video_path=INPUT_VIDEO,
            output_video_path=OUTPUT_VIDEO,
            start_text=START_TEXT,
            end_text=END_TEXT,
            start_duration=START_DURATION,
            end_duration=END_DURATION,
            start_font_path=START_FONT_PATH,
            end_font_path=END_FONT_PATH,
            start_fontsize=START_FONTSIZE,
            end_fontsize=END_FONTSIZE,
            start_position=START_POSITION,
            end_position=END_POSITION,
            text_color=TEXT_COLOR,
            bg_color=BG_COLOR,
            col_opacity=COL_OPACITY,
            padding=PADDING,
            fade_in=FADE_IN,
            fade_out=FADE_OUT,
            fade_duration=FADE_DURATION
        )
