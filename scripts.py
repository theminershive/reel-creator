import math
import openai
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from openai.error import OpenAIError
import random
import re

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG for detailed logs
logger = logging.getLogger(__name__)

# Constants
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VIDEO_SCRIPTS_DIR = "./output/video_scripts/"
MAX_SCRIPT_TOKENS = 3500  # Initial value; will be adjusted based on video length

# Set OpenAI API Key
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY is not set. Check your .env file.")
    exit(1)
openai.api_key = OPENAI_API_KEY

# Define available voices
VOICES = {
    "Luca": {
        "id": "4JVOFy4SLQs9my0OLhEw",
        "description": "A young adult American male with a calm, almost sober, slightly breathy way of talking. Great for voiceovers and narrations of all kinds.",
        "attributes": {
            "language": "English (American)",
            "mood": "Calm",
            "age": "Young",
            "gender": "Male",
            "style": "Narrative & Story"
        }
    },
    "Jessica Anne Bogart - Conversations": {
        "id": "g6xIsTj2HwM6VR4iXFCw",
        "description": "Friendly and Conversational Female voice. Articulate, Confident and Helpful. Works well for Conversations.",
        "attributes": {
            "language": "English (American)",
            "clarity": "Crisp",
            "age": "Middle-Aged",
            "gender": "Female",
            "style": "Conversational"
        }
    },
    "Christopher": {
        "id": "G17SuINrv2H9FC6nvetn",
        "description": "British male narrator, English, well-spoken, gentle and trustworthy voice. Great for audiobooks, podcasts and voiceovers.",
        "attributes": {
            "language": "English (British)",
            "mood": "Calm",
            "gender": "Male",
            "age": "Middle-Aged",
            "style": "Narrative & Story"
        }
    },
    "Brian Overturf": {
        "id": "ryn3WBvkCsp4dPZksMIf",
        "description": "Middle aged Male voice. Perfect for radio.",
        "attributes": {
            "language": "English (American)",
            "profession": "Professional",
            "gender": "Male",
            "age": "Middle-Aged",
            "style": "Narrative & Story"
        }
    },
    "Bill Oxley": {
        "id": "T5cu6IU92Krx4mh43osx",
        "description": "Middle aged American male with a clear and natural voice. Perfect for audio book and documentary narration.",
        "attributes": {
            "language": "English (American)",
            "style": "Narrative & Story",
            "clarity": "Clear",
            "gender": "Male",
            "age": "Middle-Aged"
            # Additional attributes can be added as needed
        }
    },
    "Bradley - Earnest narrator": {
        "id": "RexqLjNzkCjWogguKyff",
        "description": "Middle-aged American male, baritone voice, based on religious audiobook. Earnest and kind.",
        "attributes": {
            "mood": "Gentle",
            "age": "Middle-Aged",
            "gender": "Male",
            "language": "English (American)",
            "style": "Informative & Educational"
        }
    },
    "Valentino": {
        "id": "Nv8Euon5i3G2sBJM47fo",
        "description": "A great voice with depth. The voice is deep with a great accent, and works well for meditations and narrations.",
        "attributes": {
            "language": "British",
            "mood": "Meditative",
            "age": "Old",
            "gender": "Male",
            "style": "Narrative & Story"
        }
    },
    "Frederick Surrey": {
        "id": "j9jfwdrw7BRfcR43Qohk",
        "description": "Professional, calm well spoken British narrator full of intrigue and wonder. Suitable for Nature, Science, Mystery & History documentaries or audiobooks & narration projects that need a smooth & velvety tone.",
        "attributes": {
            "mood": "Calm",
            "age": "Middle-Aged",
            "gender": "Male",
            "language": "English (British)",
            "style": "Narrative & Story"
        }
    }
}

# Define models with their descriptions and example prompts
MODELS = {
    "Leonardo Phoenix": {
        "description": "Use this as your last when other models don't match the requirements.",
        "keywords": ["illustration", "digital art", "painting"],
        "example_prompts": [
            "Digital illustration depicting a serene suburban scene at dusk. The layout features a cozy, single-story house with warm, glowing windows, surrounded by lush greenery and colorful flowers. A vintage yellow car is parked in the driveway, which reflects the soft light from the sky. The sky is a vibrant display of pink, orange, and purple hues, with fluffy clouds scattered across it, and a crescent moon is visible. In the background, a cityscape is faintly visible, nestled at the base of distant mountains. The overall atmosphere is tranquil and picturesque, capturing the peaceful transition from day to night.",
            "Create a vibrant, cheerful cartoon-style starfish with a textured, gradient orange body that transitions from a light, creamy orange on the underside to a deep, burnt orange on the top, adorned with expressive, shimmering eyes that sparkle with joy, accompanied by intricate, swirling patterns and tiny, rounded spots in shades of coral pink and sunshine yellow, adding a playful touch to the starfish's lively demeanor, set against a subtle, soft-focus background that enhances the starfish's textural details and popping colors.",
            "A tender scene featuring a small, adorable donkey, no larger than a housecat, gently cradled in a human's cupped hand, conveying a sense of nurturing and care, with the donkey's soft, fluffy fur a warm beige color, and its large brown eyes looking trustingly upwards, its tiny nostrils flared as if sniffing the air, the human's hand a gentle, pale skin tone with a few faint freckles, the fingers wrapped delicately around the donkey's body, with a subtle hint of a smile playing on the human's lips, the overall atmosphere warm, serene, and heartwarming."
        ]
    },
    "Leonardo Anime XL": {
        "description": "A new high-speed Anime-focused model that excels at a range of anime, illustrative, and CG styles.",
        "keywords": ["anime", "manga", "cartoon"],
        "example_prompts": [
            "A radiant anime-style female knight with shimmering silver hair and glowing green eyes. She wears ornate golden armor engraved with floral patterns and a flowing white cape. Her hands hold a massive, radiant greatsword glowing with holy light. Her expression is calm and noble, embodying both grace and strength. The background features a heavenly battlefield with beams of light piercing through the clouds, casting her in a divine glow. Use soft gradients, luminous effects, and detailed engravings to highlight her celestial and majestic aura.",
            "Viral anime nature wallpaper in 4K quality, in the style of digital illustration inspired by Yoshitaka Amano, featuring a magical nighttime landscape featuring a quaint, cozy house nestled on a hillside, illuminated by warm glowing lights from its windows. A large, vibrant red tree with glowing leaves stands above the house, its branches spreading majestically. A winding stone pathway, adorned with glowing red orbs, leads up to the house. The starry sky, filled with constellations and a shimmering galaxy, creates a breathtaking backdrop, enhancing the dreamlike and enchanting atmosphere.",
            "Highly detailed, anime style, man, Sitting on the window, playing guitar, retro, set against the background is sky raining.",
            "Image is a digital artwork featuring an anime-style character with a serene expression. The character has fair skin and is depicted with closed eyes, suggesting a peaceful or contemplative mood. Her hair is styled in loose waves, with a butterfly-shaped accessory adorning it. She wears a high-collared, buttoned black dress with a white coat draped over her shoulders. The background is filled with glowing, golden sparkles and a luminous butterfly near her face, creating a magical and ethereal atmosphere. The overall color palette is warm, with shades of gold and brown dominating the scene. The artist's signature, 'Bacchus,' is elegantly written in the bottom left corner in a cursive font, adding a personal touch to the artwork."
        ]
    },
    "Leonardo Lightning XL": {
        "description": "Our new high-speed generalist image generation model. Great at everything from photorealism to painterly styles.",
        "keywords": ["photorealistic", "realistic", "portrait", "abstract", "fantasy", "nature", "environment"],
        "example_prompts": [
            "A serene landscape illuminated by a massive, glowing full moon that dominates the sky. Silvery moonlight reflects off a still, glassy lake surrounded by mist-covered trees. Fireflies hover above the water, creating a soft, twinkling effect. In the distance, a silhouette of a lone deer stands on a hill, adding a peaceful, enchanting touch.",
            "Peaceful night scene with moonlight filling the sky and misty clouds. Small house. The bright full moon illuminates the vast green fields, creating a peaceful atmosphere. 4k.",
            "Super realistic gorilla gamer with gold dollar necklace, wearing glasses playing computer games in neon room.",
            "Beautiful sunrise, fantasy-like.",
            "Rendered in 8k ultra HD, silhouette figures of a man and a woman standing under an umbrella. The umbrella is made of transparent light. The man holds the umbrella with both hands and the woman stands right in front of him. They both look at each other and seem to be engaged in a romantic moment. Rain falls on the figures, and they are surrounded by a blanket of colorful light particles. The raindrops come in various shades of pink, purple, blue, and green, sparkling like the sparkle of diamonds. The background is dark black. The overall mood of the image is peaceful and serene."
        ]
    },
    "Leonardo Kino XL": {
        "description": "A model with a strong focus on cinematic outputs. Excels at wider aspect ratios and does not need a negative prompt.",
        "keywords": ["cinematic", "movie", "film", "noir", "thriller"],
        "example_prompts": [
            "Image is a digital illustration featuring a stylized, cartoonish snake with large, expressive blue eyes and a friendly smile. The snake has a light blue body adorned with pink and white spots, and it is coiled in a playful manner. It wears an ornate, jewel-encrusted tiara with pink and blue gemstones, adding a regal touch. The background is a deep blue with snowflakes and decorative elements, including a Christmas ornament and a ribbon. In the bottom left corner, there is a small depiction of Santa Claus holding a teddy bear. The image includes Cyrillic text in red and white, adding a festive, holiday theme to the overall composition.",
            "A picturesque garden in the heart of France bursts with the enchanting beauty of white, pink, and blue peonies, their lush blooms creating a symphony of color and fragrance. Nestled around a charming countryside home with weathered stone walls and ivy-draped windows, the garden feels like a storybook scene. The white peonies exude purity and elegance, while the pink ones add a touch of romance, and the rare blue hues bring a sense of mystique. Cobblestone pathways weave through the vibrant beds, where bees and butterflies flit playfully among the flowers. The morning light bathes the garden in a warm glow, enhancing the vibrant palette and creating a serene, magical ambiance that feels uniquely French.",
            "A dramatic, cinematic portrait of a woman gently cradling a small, curious alien creature in her arms, the alien's large, round eyes gazing up at her with wonder, the woman's expression a mix of amazement and tenderness, soft, ethereal lighting, muted colors, high-contrast shadows, a sense of intimacy and connection between the two beings."
        ]
    },
}

def generate_background_music(length):
    """
    Select background music types based on video length.
    Returns a comma-separated string of one or two music types.
    """
    music_types = ["cinematic", "ambient", "suspense", "upbeat", "melodic", "neutral", "inspiring", "dramatic"]
    selected = random.sample(music_types, 2) if length > 120 else random.sample(music_types, 1)
    logger.debug(f"Selected background music: {selected}")
    return ", ".join(selected)

def generate_transition_effect():
    """
    Select a transition effect type.
    """
    transition_effects = ["swoosh", "fade-in", "whoosh", "glimmer"]
    effect = random.choice(transition_effects)
    logger.debug(f"Selected transition effect: {effect}")
    return effect

def call_openai_api(messages, max_tokens, temperature):
    """
    Calls the OpenAI API with the given messages, max tokens, and temperature.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        logger.debug("OpenAI API call successful.")
        return response
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return None

def calculate_max_tokens(length):
    """
    Calculate max tokens based on video length.
    Adjust this function as needed to correlate video length with token count.
    """
    # Example: Assume 70 tokens per second, adjust as needed
    return min(4000, length * 70)  # Cap at 4000 tokens

def select_background_music_via_gpt(topic, music_options):
    """
    Uses GPT to select the most appropriate background music from the provided options based on the video topic.

    Args:
        topic (str): The topic of the video.
        music_options (list): List of background music options.

    Returns:
        str: The selected background music.
    """
    options_str = ", ".join(music_options)
    prompt = f"""
You are an assistant that selects the most appropriate background music for a video based on its topic.

**Video Topic:** {topic}

**Available Background Music Options:** {options_str}

**Instructions:**
- Choose the most suitable background music from the list above.
- Provide only the name of the selected background music without any additional text or explanations.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are ChatGPT, a large language model trained by OpenAI."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,  # Enough to capture a single word or short phrase
            temperature=0.0  # Low temperature for deterministic output
        )

        selected_music = response.choices[0].message['content'].strip().lower()
        # Normalize the response to match the predefined options
        for music in music_options:
            if music.lower() == selected_music:
                return music
        # If GPT selects an invalid option, fallback to a default
        logger.warning(f"GPT selected an unknown background music: '{selected_music}'. Defaulting to 'neutral'.")
        return "neutral"

    except OpenAIError as e:
        logger.error(f"OpenAI API error during background music selection: {e}")
        # Default background music in case of error
        return "neutral"
    except Exception as e:
        logger.error(f"An unexpected error occurred during background music selection: {e}")
        return "neutral"

def call_openai_api_generate_script(prompt, max_tokens, temperature):
    """
    Calls OpenAI API to generate the video script based on the provided prompt.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are ChatGPT, a large language model trained by OpenAI."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        logger.debug("OpenAI API call for script generation successful.")
        return response
    except OpenAIError as e:
        logger.error(f"OpenAI API error during script generation: {e}")
        return None

def generate_video_script(topic, length, size, num_sections, num_segments):
    """
    Generates a comprehensive video script based on the provided parameters.
    Args:
        topic (str): The topic for the video script.
        length (int): Total length of the video in seconds.
        size (str): Size of the video (e.g., "1080x1920").
        num_sections (int): Number of sections in the video.
        num_segments (int): Number of segments per section.
    Returns:
        dict: The generated video script data.
    """
    try:
        # Calculate duration per segment
        duration_per_segment = int(length / (num_sections * num_segments))

        # Determine number of segments with motion
        total_segments = num_sections * num_segments
        num_motion_segments = max(1, int(total_segments * 0.3))
        motion_indices = random.sample(range(total_segments), num_motion_segments)

        
        # Adjusted durations and section logic with HOOK + OUTRO
        total_main_sections = num_sections
        total_main_segments = num_sections * num_segments
        total_segments = total_main_segments + 2  # one for hook, one for outro
        duration_per_segment = max(6, math.ceil(length / total_segments * 1.15))

        sections = []

        # HOOK
        sections.append({
            "section_number": 1,
            "title": "Hook: Attention-Grabbing Opener",
            "section_duration": duration_per_segment,
            "segments": [{
                "segment_number": 1,
                "narration": {
                    "text": "Hook narration here.",
                    "start_time": 0,
                    "duration": duration_per_segment
                },
                "visual": {
                    "type": "image",
                    "prompt": f"High-impact visual for opening on topic: {topic}.",
                    "start_time": 0,
                    "duration": duration_per_segment,
                    "apply_motion": False
                },
                "sound": {
                    "transition_effect": generate_transition_effect()
                }
            }]
        })

        # Main sections
        for i in range(num_sections):
            section = {}
            section_number = i + 2
            section["section_number"] = section_number
            section["title"] = f"Section {i + 1}: Title"
            section["section_duration"] = num_segments * duration_per_segment
            segments = []
            for j in range(num_segments):
                global_segment_index = 1 + i * num_segments + j  # shift start by 1 for HOOK
                segment_number = j + 1
                segment = {
                    "segment_number": segment_number,
                    "narration": {
                        "text": "Narration text here.",
                        "start_time": global_segment_index * duration_per_segment,
                        "duration": duration_per_segment
                    },
                    "visual": {
                        "type": "image",
                        "prompt": f"Detailed visual prompt tailored to the {topic} topic.",
                        "start_time": global_segment_index * duration_per_segment,
                        "duration": duration_per_segment,
                        "apply_motion": False
                    },
                    "sound": {
                        "transition_effect": generate_transition_effect()
                    }
                }
                segments.append(segment)
            section["segments"] = segments
            sections.append(section)

        # OUTRO
        outro_start = (total_segments - 1) * duration_per_segment
        sections.append({
            "section_number": num_sections + 2,
            "title": "Outro: Wrap-up and CTA",
            "section_duration": duration_per_segment,
            "segments": [{
                "segment_number": 1,
                "narration": {
                    "text": "Outro narration here.",
                    "start_time": outro_start,
                    "duration": duration_per_segment
                },
                "visual": {
                    "type": "image",
                    "prompt": f"Closing image to wrap up video on topic: {topic}.",
                    "start_time": outro_start,
                    "duration": duration_per_segment,
                    "apply_motion": False
                },
                "sound": {
                    "transition_effect": generate_transition_effect()
                }
            }]
        })
# Construct social media metadata if length > 120
        social_media = {}
        if length > 120:
            social_media = {
                "title": "Suggested title for social media platforms.",
                "description": "Short and engaging description for social media platforms.",
                "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
            }

        # Construct the initial JSON structure without background_music
        script_json = {
            "settings": {
                "use_background_music": True,
                "use_transitions": True,
                "video_size": size
            },
            "sections": sections
        }

        if length > 120:
            script_json["social_media"] = social_media

        # Serialize the JSON for reference (optional)


        # Prepare dynamic sections to avoid backslash issues inside f-strings
        social_media_instructions = ""
        social_media_json_block = ""
        if length > 120:
            social_media_instructions = (
                "5. **Social Media:**\n"
                "   - Generate a compelling title and description for social media platforms.\n"
                "   - Provide relevant tags to enhance discoverability."
            )
            social_media_json_block = f'"social_media": {json.dumps(social_media, indent=4)}'
        prompt_json = json.dumps(script_json, indent=4)

        # Construct the prompt for OpenAI to generate the actual script without background_music
        prompt = f"""
You are an experienced scriptwriter tasked with creating a {length}-second {'comprehensive' if length > 120 else 'engaging'} video script on the topic "{topic}".

**Settings:**
- Video Size: {size}
- Number of Sections: {num_sections}
- Number of Segments per Section: {num_segments}

**Your Task:**

1. **Sections:**
   - This video must include a total of {num_sections + 2} sections.
   - Section 1 is the **HOOK**: a single, high-impact attention-grabbing segment that introduces the topic.
   - The last section is the **OUTRO**: a single, motivational or summarizing segment that wraps up the story or leaves viewers with a final thought.
   - Between them, generate {num_sections} regular sections, each with {num_segments} segments.

1. **Sections:**
   - Section 1 should be the **HOOK**: a single, high-impact attention-grabbing segment introducing the topic.
   - The final section should be the **OUTRO**: a single wrap-up or call-to-action segment that summarizes or inspires.
   - Between them, include {num_sections} main sections, each with {num_segments} segments.

1. **Structure:**
   - Divide the video into {num_sections} sections.
   - Each section contains {num_segments} narration segments.
   - Ensure each section has a specific title and flows logically to the next.

2. **Narration:**
   - Each narration segment should last approximately {duration_per_segment} seconds.
   - Begin with a compelling hook.
   - Provide clear and concise information relevant to the topic.
   - Maintain a consistent and engaging tone.

3. **Visuals:**
   - For each narration segment, provide a detailed visual prompt.
   - Use diverse and engaging imagery that complements the narration.
   - Include an `apply_motion` tag set to `true` for approximately 30% of the segments.

4. **Sound:**
   - Suggest transition effects for each section.
   - **Note:** Background music will be assigned separately and should not be included here.

{social_media_instructions}

**Output Format:**

Provide the output in JSON format with the following structure:

{{
    "settings": {{
        "use_background_music": true,
        "use_transitions": true,
        "video_size": "{size}"
    }},
    "sections": [
        {{
            "section_number": {i + 1},
            "title": "Section {i + 1}: Title",
            "section_duration": {int(length / num_sections)},
            "segments": [
                {{
                    "segment_number": 1,
                    "narration": {{
                        "text": "Narration text here.",
                        "start_time": 0,
                        "duration": {duration_per_segment}
                    }},
                    "visual": {{
                        "type": "image",
                        "prompt": "Detailed visual prompt tailored to the {topic} topic.",
                        "start_time": 0,
                        "duration": {duration_per_segment},
                        "apply_motion": false
                    }},
                    "sound": {{
                        "transition_effect": "{generate_transition_effect()}"
                    }}
                }}
            ]
        }}
    ]{"," if length > 120 else ""}
    {social_media_json_block}
}}

**Important Instructions:**

- **Provide only the JSON output** in your response. Do not include any explanations, reasoning, or additional text outside the JSON.
- **Do not use Markdown formatting** or include code blocks. The JSON should be plain text starting with `{{` and ending with `}}`.
        """

        # Call OpenAI API to generate the script
        response = call_openai_api_generate_script(
            prompt=prompt,
            max_tokens=MAX_SCRIPT_TOKENS,
            temperature=0.7
        )

        if not response:
            logger.error("Failed to retrieve video script.")
            return None

        script_content = response.choices[0].message['content']
        logger.debug(f"Raw response content:\n{script_content}")

        

# Parse JSON
        try:
            script_data = json.loads(script_content.strip())
            logger.debug(f"Generated script data: {json.dumps(script_data, indent=2)}")
            early_path = os.path.join(VIDEO_SCRIPTS_DIR, f"{topic.lower().replace(' ', '_')}_raw.json")
            with open(early_path, 'w', encoding='utf-8') as f:
                json.dump(script_data, f, indent=4)
            logger.info(f"Raw script saved early at: {early_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode GPT script output: {e}")
            return None
        # Inject missing transition effects

        for sec in script_data.get("sections", []):

            for seg in sec.get("segments", []):

                seg.setdefault("sound", {})["transition_effect"] = seg.get("sound", {}).get("transition_effect", generate_transition_effect())


        # Combine narration texts for voice and style selection

        narration_texts = []

        for sec in script_data.get("sections", []):

            if "segments" in sec:

                for seg in sec["segments"]:

                    t = seg.get("narration", {}).get("text", "")

                    if t:

                        narration_texts.append(t)

            else:

                t = sec.get("narration", {}).get("text", "")

                if t:

                    narration_texts.append(t)


        combined_text = " ".join(narration_texts)


        # Select voice and style, and set background music

        script_data["tone"] = select_voice(combined_text)

        selected_style, _ = select_style(combined_text)

        script_data["image_style"] = selected_style

        script_data["background_music"] = generate_background_music(length)


        return script_data


    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        return None
def select_voice(script_text):
    """
    Selects the most appropriate voice from the VOICES dictionary based on the complete script.

    Args:
        script_text (str): The complete narration text of the script.

    Returns:
        str: The name of the selected voice.
    """
    # Prepare the voice options information
    voice_options = "\n".join([
        f"- **{voice_name}**: {voice_info['description']}"
        for voice_name, voice_info in VOICES.items()
    ])

    prompt = f"""
Given the following script narration:

\"\"\"
{script_text}
\"\"\"

And the following list of available voices:

{voice_options}

Please analyze the script and select the most appropriate voice for the narration from the list above.

**Instructions:**
- Choose the voice that best matches the script's content and tone.
- Provide only the name of the selected voice without any additional text.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are ChatGPT, an assistant that selects the most appropriate narration voice based on script content and provided voice options."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0.0  # Ensures consistent and deterministic output
        )

        selected_voice = response.choices[0].message['content'].strip()
        logger.debug(f"Selected voice by GPT: {selected_voice}")

        # Validate the selected voice
        if selected_voice in VOICES:
            return selected_voice
        else:
            logger.warning(f"GPT selected an unknown voice: '{selected_voice}'. Defaulting to 'Frederick Surrey'.")
            return "Frederick Surrey"

    except OpenAIError as e:
        logger.error(f"OpenAI API error during voice selection: {e}")
        # Default voice in case of error
        return "Frederick Surrey"
    except Exception as e:
        logger.error(f"An unexpected error occurred during voice selection: {e}")
        # Default voice in case of error
        return "Frederick Surrey"

def select_style(script_text):
    """
    Selects the most appropriate style by sending the script back to GPT along with the style list.
    Args:
        script_text (str): The entire script narration.
    Returns:
        tuple: Selected style name and its corresponding model info.
    """
    # Construct the styles description
    styles_description = "\n".join([
        f"- **{style_name}**: {info['description']} Keywords: {', '.join(info['keywords'])}"
        for style_name, info in MODELS.items()
    ])

    prompt = f"""
Given the following video script narration:

\"\"\"
{script_text}
\"\"\"

And the following list of styles:

{styles_description}

Please analyze the script narration and select the most appropriate style from the list above that best matches the content and tone of the script. Provide only the name of the selected style.
    """

    # Call the OpenAI API
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.3  # Lower temperature for consistency
        )

        selected_style = response.choices[0].message['content'].strip()
        logger.debug(f"Selected style from GPT:\n{selected_style}")

        # Validate the selected style
        if selected_style in MODELS:
            model_info = MODELS[selected_style]
            return selected_style, model_info
        else:
            logger.error(f"GPT returned an unknown style: {selected_style}. Selecting a random style.")
            selected_style = random.choice(list(MODELS.keys()))
            model_info = MODELS[selected_style]
            return selected_style, model_info

    except OpenAIError as e:
        logger.error(f"OpenAI API error during style selection: {e}")
        # In case of error, select a random style
        selected_style = random.choice(list(MODELS.keys()))
        model_info = MODELS[selected_style]
        return selected_style, model_info

    except Exception as e:
        logger.error(f"An unexpected error occurred during style selection: {e}")
        selected_style = random.choice(list(MODELS.keys()))
        model_info = MODELS[selected_style]
        return selected_style, model_info

def update_visual_prompts(script_data, style_info):
    """
    Updates the visual prompts in the script data based on the selected style.
    Args:
        script_data (dict): The script data containing sections and segments.
        style_info (dict): The selected style information from MODELS.
    """
    style_description = style_info["description"]
    example_prompts = "\n".join(style_info["example_prompts"])

    for section in script_data.get("sections", []):
        # For sections with segments
        if "segments" in section:
            for segment in section["segments"]:
                narration_text = segment["narration"].get("text", "")
                if not narration_text:
                    continue
                # Generate new visual prompt
                prompt = f"""
Given the following narration text:

\"\"\"
{narration_text}
\"\"\"

And the following style description:

{style_description}

With these example prompts:

{example_prompts}

Generate a detailed visual prompt that complements the narration and adheres to the style guidelines.

Provide only the visual prompt text without any additional explanations.
                """

                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=150,
                        temperature=0.7
                    )
                    visual_prompt = response.choices[0].message['content'].strip()
                    logger.debug(f"Generated visual prompt:\n{visual_prompt}")
                    segment["visual"]["prompt"] = visual_prompt
                except OpenAIError as e:
                    logger.error(f"OpenAI API error during visual prompt generation: {e}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred during visual prompt generation: {e}")
        else:
            # For sections without segments (short videos)
            narration_text = section.get("narration", {}).get("text", "")
            if not narration_text:
                continue
            # Generate new visual prompt
            prompt = f"""
Given the following narration text:

\"\"\"
{narration_text}
\"\"\"

And the following style description:

{style_description}

With these example prompts:

{example_prompts}

Generate a detailed visual prompt that complements the narration and adheres to the style guidelines.

Provide only the visual prompt text without any additional explanations.
            """

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.7
                )
                visual_prompt = response.choices[0].message['content'].strip()
                logger.debug(f"Generated visual prompt:\n{visual_prompt}")
                section["visual"]["prompt"] = visual_prompt
            except OpenAIError as e:
                logger.error(f"OpenAI API error during visual prompt generation: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred during visual prompt generation: {e}")

def save_script(script_data, tone, style, topic, filename=None):
    """
    Saves the generated script, tone, and style to a JSON file.
    Args:
        script_data (dict): The generated script data.
        tone (str): The name of the selected voice.
        style (str): The selected style name (optional).
        topic (str): The topic of the video.
        filename (str, optional): The filename for the saved script. Defaults to None.
    Returns:
        str: The path to the saved script file.
    """
    if not filename:
        # Replace any invalid filename characters
        safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic)
        filename = f"{safe_topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    script_path = os.path.join(VIDEO_SCRIPTS_DIR, filename)

    # Ensure the directory exists
    os.makedirs(VIDEO_SCRIPTS_DIR, exist_ok=True)

    # Add tone and style to the script data
    script_data["tone"] = tone
    if style:
        script_data["settings"]["image_generation_style"] = style
        script_data["settings"]["style_selection_reason"] = f"The {style} style was selected based on the script content."

    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            json.dump(script_data, f, indent=4)
        logger.info(f"Script, tone, and style saved to {script_path}")
        return script_path
    except Exception as e:
        logger.error(f"An error occurred while saving the script: {e}")
        return None

def select_voice_and_style(script_text):
    """
    Selects the most appropriate voice and style based on the complete script.

    Args:
        script_text (str): The complete narration text of the script.

    Returns:
        tuple: Selected voice name, selected style name, and style info.
    """
    selected_voice = select_voice(script_text)
    selected_style, style_info = select_style(script_text)
    return selected_voice, selected_style, style_info

def main():
    """
    Main function to generate, select voice and style, update visuals, and save a video script.
    """
    try:
        # Gather user inputs
        topic = input("Enter the topic of the video: ").strip()
        length_input = input("Enter the length of the video in seconds: ").strip()
        size = input("Enter the size of the video (e.g., 1080x1920): ").strip()
        num_sections_input = input("Enter the number of sections: ").strip()
        num_segments_input = input("Enter the number of segments per section: ").strip()

        # Validate numeric inputs
        try:
            length = int(length_input)
            num_sections = int(num_sections_input)
            num_segments = int(num_segments_input)
        except ValueError:
            logger.error("Invalid input. Length, number of sections, and number of segments must be integers.")
            print("Invalid input. Please ensure that length, number of sections, and number of segments are numbers.")
            return

        # Adjust MAX_SCRIPT_TOKENS based on video length
        global MAX_SCRIPT_TOKENS
        MAX_SCRIPT_TOKENS = calculate_max_tokens(length)
        logger.debug(f"Adjusted MAX_SCRIPT_TOKENS based on video length: {MAX_SCRIPT_TOKENS}")

        # Generate the video script
        script_data = generate_video_script(topic, length, size, num_sections, num_segments)

        if not script_data:
            print("Failed to generate the script. Please check the logs for more details.")
            return

        # Combine all narration texts for voice and style selection
        narration_texts = []
        for section in script_data.get("sections", []):
            if "segments" in section:
                for segment in section["segments"]:
                    narration_text = segment.get("narration", {}).get("text", "")
                    if narration_text:
                        narration_texts.append(narration_text)
            else:
                narration_text = section.get("narration", {}).get("text", "")
                if narration_text:
                    narration_texts.append(narration_text)

        combined_narration = " ".join(narration_texts)
        logger.debug(f"Combined narration text for voice and style selection:\n{combined_narration}")

        # Select the appropriate voice and style based on the combined narration
        selected_voice, selected_style, style_info = select_voice_and_style(combined_narration)
        logger.info(f"Selected voice: {selected_voice}")
        logger.info(f"Selected style: {selected_style}")

        # Update the visual prompts based on the selected style
        update_visual_prompts(script_data, style_info)

        # Save the script with tone (voice) and style information
        saved_path = save_script(script_data, selected_voice, selected_style, topic)

        if saved_path:
            print(f"Script generation, voice and style selection, and saving completed successfully.\nSaved to: {saved_path}")
        else:
            print("Script generated, but failed to save the file.")

    except Exception as e:
        logger.error(f"An unexpected error occurred in the main function: {e}")
        print("An unexpected error occurred. Please check the logs for more details.")

if __name__ == '__main__':
    main()
