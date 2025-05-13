# sabik_agent/utils.py
import base64
import os
import mimetypes
import requests
from PIL import Image
from io import BytesIO

from .interface import console, Panel
from .config import OUTPUT_DIR

def encode_image_base64(image_path_or_url):
    try:
        if image_path_or_url.startswith(('http://', 'https://')):
            console.print(f"Fetching image: [link={image_path_or_url}]{image_path_or_url}[/link]")
            response = requests.get(image_path_or_url, timeout=15)
            response.raise_for_status()
            image_data = response.content
            content_type = response.headers.get('Content-Type', 'image/jpeg')
        else:
            if not os.path.exists(image_path_or_url):
                raise FileNotFoundError(f"Image not found: {image_path_or_url}")
            console.print(f"Encoding image: [cyan]{image_path_or_url}[/cyan]")
            with open(image_path_or_url, "rb") as f:
                image_data = f.read()
            mime_type, _ = mimetypes.guess_type(image_path_or_url)
            content_type = mime_type or 'image/jpeg'
        
        # Try to verify and get more precise mime type with Pillow
        try:
            img = Image.open(BytesIO(image_data))
            img.verify() # Verifies if it's a valid image
            fmt_map = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'GIF': 'image/gif', 'WEBP': 'image/webp'}
            detected_mime = fmt_map.get(img.format) # Pillow's detected format
            if detected_mime:
                content_type = detected_mime
            img.close()
        except Exception as img_err:
            console.print(f"[yellow]Warn:[/yellow] Pillow verification/format detection failed for '{image_path_or_url}'. Using initial type: {content_type}. Error: {img_err}")

        return f"data:{content_type};base64,{base64.b64encode(image_data).decode('utf-8')}"
    except Exception as e:
        console.print(Panel(f"{str(e)}", title="[bold red]Image Encode Error[/]", border_style="red"))
        return None

def encode_audio_base64(audio_path):
    try:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio not found: {audio_path}")
        console.print(f"Encoding audio: [cyan]{audio_path}[/cyan]")
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        base64_audio = base64.b64encode(audio_data).decode('utf-8')
        audio_format = os.path.splitext(audio_path)[1].lower().lstrip('.')
        if not audio_format:
            console.print(f"[yellow]Warn:[/yellow] Could not determine audio format for {audio_path}. Assuming 'mp3'.")
            audio_format = 'mp3' # Default assumption
        return base64_audio, audio_format
    except Exception as e:
        console.print(Panel(f"{str(e)}", title="[bold red]Audio Encode Error[/]", border_style="red"))
        return None, None

def save_base64_audio(base64_data, filename="output_audio.mp3"):
    try:
        audio_binary = base64.b64decode(base64_data)
        os.makedirs(OUTPUT_DIR, exist_ok=True) # Ensure OUTPUT_DIR exists
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(audio_binary)
        console.print(f"Audio saved: [bright_blue u]{filepath}[/bright_blue u]")
        return filepath
    except Exception as e:
        console.print(Panel(f"{str(e)}", title="[bold red]Audio Save Error[/]", border_style="red"))
        return None