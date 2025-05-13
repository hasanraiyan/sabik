import requests
import os
import time
import urllib.parse

from ..interface import console, Panel
from ..config import OUTPUT_DIR, OPENAI_IMAGE_BASE_URL_TEXT

def _api_generate_image_get(session, referrer, prompt, model=None, width=None, height=None, seed=None, nologo=None, enhance=None, safe=None):
    params = {"model": model, "width": width, "height": height, "seed": seed, "nologo": nologo, "enhance": enhance, "safe": safe, "referrer": referrer}
    params = {k: v for k, v in params.items() if v is not None}
    encoded_prompt = urllib.parse.quote(prompt, safe='')
    url = f"{OPENAI_IMAGE_BASE_URL_TEXT}/prompt/{encoded_prompt}"
    response = None
    try:
        console.print(Panel(f"Prompt: {prompt}\nModel: {model or 'default'}", title="[bold blue]API Call: GET Image[/]", border_style="blue", expand=False))
        response = session.get(url, params=params, timeout=300)
        response.raise_for_status()
        if 'image/' in response.headers.get('Content-Type', ''):
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            safe_prompt = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in prompt[:40]).rstrip().replace(' ', '_')
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            ext = content_type.split('/')[-1].split(';')[0]
            if not ext or len(ext) > 5: ext = 'jpg'
            filename = f"image_{safe_prompt}_{int(time.time())}.{ext}"
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, 'wb') as f: f.write(response.content)
            console.print(f"Image saved: [bright_blue u]{filepath}[/bright_blue u]")
            return response.url
        else:
            console.print(Panel(f"Expected image, got {response.headers.get('Content-Type')}\n{response.text[:200]}", title="[bold red]API Error[/]", border_style="red"))
            return None
    except requests.exceptions.Timeout:
        console.print(Panel("Timeout during image generation.", title="[bold red]Timeout Error[/]", border_style="red"))
        return None
    except requests.exceptions.RequestException as e:
        status_code = response.status_code if response else "N/A"
        console.print(Panel(f"Error: {e}\nStatus: {status_code}", title="[bold red]Request Error[/]", border_style="red"))
        return None
    except Exception as e:
        console.print(Panel(f"Image generation/save error: {e}", title="[bold red]Save Error[/]", border_style="red"))
        return None

def generate_ai_image(prompt, model=None, width=None, height=None, seed=None, nologo=None, *, session, client, config, **kwargs):
    console.print(Panel(f"Tool: Generate Image\nPrompt: '{prompt}'", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    image_url = _api_generate_image_get(session, config.REFERRER_ID, prompt=prompt, model=model, width=width, height=height, seed=seed, nologo=nologo)
    if image_url:
        return {"status": "success", "image_url": image_url, "message": f"Image generated, available at {image_url}"}
    else:
        return {"status": "error", "message": f"Failed to generate image for prompt: '{prompt}'."}
