import os
import json
import time
import requests
import logging
from dotenv import load_dotenv
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("leonardo_downloader.log")  # Optional: Log to a file
    ]
)

# Load environment variables from .env file
load_dotenv()

# Configuration
API_KEY = os.getenv('LEONARDO_API_KEY')
if not API_KEY:
    logging.error("API key not found. Please set LEONARDO_API_KEY in your .env file.")
    exit(1)

AUTHORIZATION = f"Bearer {API_KEY}"

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": AUTHORIZATION
}

LEONARDO_API_ENDPOINT = "https://cloud.leonardo.ai/api/rest/v1"

OUTPUT_DIR = "downloaded_content"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define custom models with complete configuration
CUSTOM_MODELS = [
    {
        "id": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",
        "name": "Leonardo Phoenix",
        "width": 576,
        "height": 1024,
        "num_images": 2,
        "alchemy": True,
        "enhancePrompt": False,
        "photoReal": False,
        "photoRealVersion": "",
        "presetStyle": "CINEMATIC"
    },
    {
        "id": "e71a1c2f-4f80-4800-934f-2c68979d8cc8",
        "name": "Leonardo Anime XL",
        "width": 512,
        "height": 1024,
        "num_images": 2,
        "alchemy": True,
        "enhancePrompt": False,
        "photoReal": False,
        "photoRealVersion": "",
        "presetStyle": "ANIME"
    },
    {
        "id": "b24e16ff-06e3-43eb-8d33-4416c2d75876",
        "name": "Leonardo Lightning XL",
        "width": 512,
        "height": 1024,
        "num_images": 2,
        "alchemy": True,
        "enhancePrompt": False,
        "photoReal": True,
        "photoRealVersion": "v2",
        "presetStyle": "PHOTOREALISTIC"
    },
    {
        "id": "aa77f04e-3eec-4034-9c07-d0f619684628",
        "name": "Leonardo Kino XL",
        "width": 512,
        "height": 1024,
        "num_images": 2,
        "alchemy": True,
        "enhancePrompt": False,
        "photoReal": True,
        "photoRealVersion": "v2",
        "presetStyle": "CINEMATIC"
    },
    ]

def get_model_config_by_style(style_name):
    for model in CUSTOM_MODELS:
        if model['name'].lower() == style_name.lower():
            logging.info(f"Selected model '{model['name']}' with ID: {model['id']}")
            return model
    logging.error(f"Style '{style_name}' not found in custom models.")
    raise ValueError(f"Style '{style_name}' not found.")

def generate_image(prompt, model_config):
    url = f"{LEONARDO_API_ENDPOINT}/generations"
    payload = {
        "height": model_config['height'],
        "modelId": model_config['id'],
        "prompt": prompt,
        "width": model_config['width'],
        "num_images": model_config['num_images'],
        "alchemy": model_config['alchemy'],
        "photoReal": model_config['photoReal'],
        "photoRealVersion": model_config['photoRealVersion'],
        "enhancePrompt": model_config['enhancePrompt'],
        "presetStyle": model_config['presetStyle']
    }

    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        # Attempt to extract generation_id from 'generations_by_pk'
        generation_id = data.get('generations_by_pk', {}).get('id')
        if generation_id:
            logging.info(f"Image generation initiated. Generation ID: {generation_id}")
            return generation_id

        # Fallback to 'sdGenerationJob'
        generation_id = data.get('sdGenerationJob', {}).get('generationId')
        if generation_id:
            logging.info(f"Image generation initiated. Generation ID: {generation_id}")
            return generation_id

        # If neither key is present
        logging.error(f"No generation ID found in response: {json.dumps(data, indent=4)}")
        return None

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred during image generation: {http_err}")
        if response is not None:
            logging.error(f"Response Content: {response.text}")
    except Exception as err:
        logging.error(f"An error occurred during image generation: {err}")
    return None

def generate_video(image_id, motion_strength=5):
    url = f"{LEONARDO_API_ENDPOINT}/generations-motion-svd"
    payload = {
        "imageId": image_id,
        "motionStrength": motion_strength
    }

    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        generation_id = data.get('motionSvdGenerationJob', {}).get('generationId')
        if generation_id:
            logging.info(f"Video generation initiated. Generation ID: {generation_id}")
            return generation_id
        else:
            logging.error(f"No generation ID found in response: {json.dumps(data, indent=4)}")
            return None
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred during video generation: {http_err}")
        if response is not None:
            logging.error(f"Response Content: {response.text}")
    except Exception as err:
        logging.error(f"An error occurred during video generation: {err}")
    return None

def poll_generation_status(generation_id, wait_time=10, max_retries=30):
    url = f"{LEONARDO_API_ENDPOINT}/generations/{generation_id}"

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()

            # Determine the status based on available keys
            status = (
                data.get('status') or
                data.get('generations_by_pk', {}).get('status') or
                data.get('sdGenerationJob', {}).get('status') or
                data.get('motionSvdGenerationJob', {}).get('status')
            )
            if status:
                status = status.lower()

            logging.info(f"Polling attempt {attempt}/{max_retries}. Status: {status}")

            if status == 'complete':
                logging.info("Generation complete.")
                return data
            elif status == 'failed':
                logging.error("Generation failed.")
                return None
            else:
                time.sleep(wait_time)
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error during status polling: {http_err}")
            if response is not None:
                logging.error(f"Response Content: {response.text}")
        except Exception as err:
            logging.error(f"An error occurred during status polling: {err}")

    logging.error("Exceeded maximum polling attempts. Generation incomplete.")
    return None

def download_content(url, filename):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(filename, 'wb') as f:
            for chunk in response.iter_content(1024):
                if chunk:
                    f.write(chunk)
        logging.info(f"Content downloaded and saved as {filename}")
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred while downloading content: {http_err}")
    except Exception as err:
        logging.error(f"An error occurred while downloading content: {err}")

def extract_image_id(data):
    try:
        # Attempt to extract from 'generations_by_pk'
        generated_images = data.get('generations_by_pk', {}).get('generated_images', [])
        if generated_images:
            image_id = generated_images[0].get('id')
            if image_id:
                logging.info(f"Extracted Image ID: {image_id}")
                return image_id

        # Fallback to 'sdGenerationJob'
        image_id = data.get('sdGenerationJob', {}).get('generationId')
        if image_id:
            logging.info(f"Extracted Image ID: {image_id}")
            return image_id

        logging.error(f"No generated images found in data: {json.dumps(data, indent=4)}")
    except Exception as err:
        logging.error(f"Error extracting image ID: {err}")
    return None

def extract_image_url(data):
    try:
        # Attempt to extract from 'generations_by_pk'
        generated_images = data.get('generations_by_pk', {}).get('generated_images', [])
        if generated_images:
            image_url = generated_images[0].get('url')
            if image_url:
                logging.info(f"Extracted Image URL: {image_url}")
                return image_url

        # Fallback to 'sdGenerationJob'
        image_url = data.get('sdGenerationJob', {}).get('imageUrl')
        if image_url:
            logging.info(f"Extracted Image URL: {image_url}")
            return image_url

        logging.error(f"No generated images found in data: {json.dumps(data, indent=4)}")
    except Exception as err:
        logging.error(f"Error extracting image URL: {err}")
    return None

def extract_video_url(data):
    try:
        # Attempt to extract from 'motionSvdGenerationJob'
        generated_videos = data.get('motionSvdGenerationJob', {}).get('generated_videos', [])
        if generated_videos:
            video_url = generated_videos[0].get('url')
            if video_url:
                logging.info(f"Extracted Video URL: {video_url}")
                return video_url

        # Fallback to motionMP4URL in 'generations_by_pk' -> 'generated_images'
        generated_images = data.get('generations_by_pk', {}).get('generated_images', [])
        if generated_images:
            motion_mp4_url = generated_images[0].get('motionMP4URL')
            if motion_mp4_url:
                logging.info(f"Extracted Video URL: {motion_mp4_url}")
                return motion_mp4_url

        # Additional fallback: Check 'sdGenerationJob' for any video URL fields
        motion_mp4_url = data.get('sdGenerationJob', {}).get('motionMP4URL')
        if motion_mp4_url:
            logging.info(f"Extracted Video URL: {motion_mp4_url}")
            return motion_mp4_url

        logging.error(f"No generated videos found in data: {json.dumps(data, indent=4)}")
    except Exception as err:
        logging.error(f"Error extracting video URL: {err}")
    return None

def process_section(section, index, model_config):
    visual = section.get('visual', {})
    segments = section.get('segments', [])

    if segments:
        # Process each segment
        for seg_idx, segment in enumerate(segments, start=1):
            visual = segment.get('visual', {})
            prompt = visual.get('prompt')
            apply_motion = visual.get('apply_motion', False)

            if not prompt:
                logging.warning(f"Section {index} Segment {seg_idx} has no prompt. Skipping.")
                continue

            logging.info(f"\nProcessing Section {index} Segment {seg_idx}:")
            logging.info(f"Prompt: {prompt}")
            logging.info(f"Apply Motion: {apply_motion}")

            image_generation_id = generate_image(prompt=prompt, model_config=model_config)
            if not image_generation_id:
                logging.error(f"Section {index} Segment {seg_idx}: Image generation failed. Skipping to next segment.")
                continue

            image_generation_data = poll_generation_status(generation_id=image_generation_id)
            if not image_generation_data:
                logging.error(f"Section {index} Segment {seg_idx}: Image generation did not complete successfully. Skipping to next segment.")
                continue

            first_image_id = extract_image_id(image_generation_data)
            first_image_url = extract_image_url(image_generation_data)

            if not first_image_id or not first_image_url:
                logging.error(f"Section {index} Segment {seg_idx}: Failed to extract image details. Skipping to next segment.")
                continue

            parsed_image_url = urlparse(first_image_url)
            image_extension = os.path.splitext(parsed_image_url.path)[-1] or ".jpg"
            image_filename = os.path.join(OUTPUT_DIR, f"section_{index}_segment_{seg_idx}_image{image_extension}")
            logging.info(f"Section {index} Segment {seg_idx}: Downloading image to '{image_filename}'.")
            download_content(first_image_url, image_filename)
            segment['visual']['image_path'] = image_filename

            if apply_motion:
                video_generation_id = generate_video(image_id=first_image_id, motion_strength=5)
                if not video_generation_id:
                    logging.error(f"Section {index} Segment {seg_idx}: Video generation failed.")
                    continue

                video_generation_data = poll_generation_status(generation_id=video_generation_id)
                if not video_generation_data:
                    logging.error(f"Section {index} Segment {seg_idx}: Video generation did not complete successfully.")
                    continue

                video_url = extract_video_url(video_generation_data)
                if not video_url:
                    logging.error(f"Section {index} Segment {seg_idx}: Failed to extract video URL.")
                    continue

                parsed_video_url = urlparse(video_url)
                video_extension = os.path.splitext(parsed_video_url.path)[-1] or ".mp4"
                video_filename = os.path.join(OUTPUT_DIR, f"section_{index}_segment_{seg_idx}_video{video_extension}")
                logging.info(f"Section {index} Segment {seg_idx}: Downloading video to '{video_filename}'.")
                download_content(video_url, video_filename)
                segment['visual']['video_path'] = video_filename
    else:
        # Process visual directly under section
        prompt = visual.get('prompt')
        apply_motion = visual.get('apply_motion', False)

        if not prompt:
            logging.warning(f"Section {index} has no prompt. Skipping.")
            return section

        logging.info(f"\nProcessing Section {index}:")
        logging.info(f"Prompt: {prompt}")
        logging.info(f"Apply Motion: {apply_motion}")

        image_generation_id = generate_image(prompt=prompt, model_config=model_config)
        if not image_generation_id:
            logging.error(f"Section {index}: Image generation failed. Skipping to next section.")
            return section

        image_generation_data = poll_generation_status(generation_id=image_generation_id)
        if not image_generation_data:
            logging.error(f"Section {index}: Image generation did not complete successfully. Skipping to next section.")
            return section

        first_image_id = extract_image_id(image_generation_data)
        first_image_url = extract_image_url(image_generation_data)

        if not first_image_id or not first_image_url:
            logging.error(f"Section {index}: Failed to extract image details. Skipping to next section.")
            return section

        parsed_image_url = urlparse(first_image_url)
        image_extension = os.path.splitext(parsed_image_url.path)[-1] or ".jpg"
        image_filename = os.path.join(OUTPUT_DIR, f"section_{index}_image{image_extension}")
        logging.info(f"Section {index}: Downloading image to '{image_filename}'.")
        download_content(first_image_url, image_filename)
        section['visual']['image_path'] = image_filename

        if apply_motion:
            video_generation_id = generate_video(image_id=first_image_id, motion_strength=5)
            if not video_generation_id:
                logging.error(f"Section {index}: Video generation failed.")
                return section

            video_generation_data = poll_generation_status(generation_id=video_generation_id)
            if not video_generation_data:
                logging.error(f"Section {index}: Video generation did not complete successfully.")
                return section

            video_url = extract_video_url(video_generation_data)
            if not video_url:
                logging.error(f"Section {index}: Failed to extract video URL.")
                return section

            parsed_video_url = urlparse(video_url)
            video_extension = os.path.splitext(parsed_video_url.path)[-1] or ".mp4"
            video_filename = os.path.join(OUTPUT_DIR, f"section_{index}_video{video_extension}")
            logging.info(f"Section {index}: Downloading video to '{video_filename}'.")
            download_content(video_url, video_filename)
            section['visual']['video_path'] = video_filename

    return section  # Ensure the section is returned after processing

def process_video_script(script_path, visuals_dir, output_script_path):
    os.makedirs(visuals_dir, exist_ok=True)

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_data = json.load(f)

        settings = script_data.get('settings', {})
        image_generation_style = settings.get('image_generation_style', "Leonardo Phoenix")
        try:
            model_config = get_model_config_by_style(image_generation_style)
        except ValueError:
            logging.error("Using default model due to style mapping failure.")
            model_config = CUSTOM_MODELS[0]

        sections = script_data.get('sections', [])
        if not sections:
            logging.error("No sections found in the script.")
            return script_path

        updated_sections = []

        for idx, section in enumerate(sections, start=1):
            logging.info(f"\n--- Processing Section {idx} ---")
            updated_section = process_section(section, idx, model_config)
            updated_sections.append(updated_section)

        script_data['sections'] = updated_sections
        with open(output_script_path, 'w', encoding='utf-8') as f:
            json.dump(script_data, f, indent=4)

        logging.info(f"Updated script saved to {output_script_path}")
        return output_script_path

    except Exception as e:
        logging.error(f"An error occurred while processing the video script: {e}")
        return script_path

def main():
    updated_script_path = 'video_script_with_visuals_and_audio.json'
    process_video_script('video_script.json', OUTPUT_DIR, updated_script_path)

if __name__ == "__main__":
    main()
