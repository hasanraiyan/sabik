# sabik_agent/tools.py
import requests
import json
import os
import time
import urllib.parse

from . import utils
from .config import OUTPUT_DIR, OPENAI_IMAGE_BASE_URL_TEXT, OPENAI_BASE_URL_TEXT
from .interface import console, Panel, Syntax

# --- Tool Helper API Call Functions ---
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
            if not ext or len(ext) > 5: ext = 'jpg' # Basic fallback
            filename = f"image_{safe_prompt}_{int(time.time())}.{ext}"
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, 'wb') as f: f.write(response.content)
            console.print(f"Image saved: [bright_blue u]{filepath}[/bright_blue u]")
            return response.url # Return the direct URL from pollinations if successful
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

def _api_generate_speech_post(session, referrer, text, voice="alloy"):
    payload = {"model": "openai-audio", "messages": [{"role": "user", "content": text}], "voice": voice, "referrer": referrer}
    url = OPENAI_BASE_URL_TEXT
    response = None
    try:
        console.print(Panel(f"Text: {text[:50]}...\nVoice: {voice}", title="[bold blue]API Call: POST TTS[/]", border_style="blue", expand=False))
        response = session.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=120)
        response.raise_for_status()
        response_data = response.json()
        audio_base64 = response_data.get('choices', [{}])[0].get('message', {}).get('audio', {}).get('data')
        if not audio_base64 or not isinstance(audio_base64, str):
            raise ValueError(f"No valid audio data found in response: {response.text[:200]}")
        
        safe_text = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in text[:30]).rstrip().replace(' ', '_')
        filename = f"speech_{safe_text}_{voice}_{int(time.time())}.mp3"
        return utils.save_base64_audio(audio_base64, filename)
    except requests.exceptions.RequestException as e:
        status_code = response.status_code if response else "N/A"
        console.print(Panel(f"Error: {e}\nStatus: {status_code}", title="[bold red]TTS Request Error[/]", border_style="red"))
        return None
    except (KeyError, IndexError, TypeError, ValueError) as e:
        resp_text = response.text[:200] if response else "N/A"
        console.print(Panel(f"Parse Error: {e}\nResponse: {resp_text}", title="[bold red]TTS Parse Error[/]", border_style="red"))
        return None
    except Exception as e:
        console.print(Panel(f"TTS generation error: {e}", title="[bold red]TTS Error[/]", border_style="red"))
        return None

def _api_call_llm_for_vision_or_stt(client, messages, model):
     payload = {"model": model, "messages": messages, "stream": False}
     try:
        console.print(Panel(f"Model: {model}", title=f"[bold blue]Internal API Call: {model}[/]", border_style="blue", expand=False, width=80))
        response = client.chat.completions.create(**payload) # client is openai.OpenAI instance
        if not response.choices:
            console.print("[red]Error: No choices from API.[/red]")
            return None
        content = response.choices[0].message.content
        console.print(Panel(f"{content[:150]}...", title="[bold green]Internal Result[/]", border_style="green", expand=False, width=80))
        return content
     except Exception as e:
        console.print(Panel(f"Error: {e}", title=f"[bold red]{model} API Error[/]", border_style="red"))
        return None

# --- Tool Function Implementations ---
def generate_ai_image(prompt, model=None, width=None, height=None, seed=None, nologo=None, *, session, client, config, **kwargs): # client not used directly, but good to have consistent signature
    console.print(Panel(f"Tool: Generate Image\nPrompt: '{prompt}'", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    image_url = _api_generate_image_get(session, config.REFERRER_ID, prompt=prompt, model=model, width=width, height=height, seed=seed, nologo=nologo)
    if image_url:
        return {"status": "success", "image_url": image_url, "message": f"Image generated, available at {image_url}"}
    else:
        return {"status": "error", "message": f"Failed to generate image for prompt: '{prompt}'."}

def analyze_image_content(image_url_or_path, analysis_prompt="Describe the image in detail.", *, session, client, config, **kwargs): # session not used directly
    console.print(Panel(f"Tool: Analyze Image\nSource: {image_url_or_path}\nPrompt: '{analysis_prompt}'", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    base64_image_data = utils.encode_image_base64(image_url_or_path)
    if not base64_image_data:
        return {"status": "error", "message": f"Could not load or encode image: {image_url_or_path}"}
    
    messages = [
        {"role": "system", "content": "You are an AI vision expert."},
        {"role": "user", "content": [
            {"type": "text", "text": analysis_prompt},
            {"type": "image_url", "image_url": {"url": base64_image_data}}
        ]}
    ]
    analysis = _api_call_llm_for_vision_or_stt(client, messages, model="openai-large") # Using openai-large as per original
    if analysis:
        return {"status": "success", "analysis": analysis}
    else:
        return {"status": "error", "message": "Image analysis failed using the vision model."}

def transcribe_audio_file(audio_file_path, *, session, client, config, **kwargs): # session not used directly
    console.print(Panel(f"Tool: Transcribe Audio\nFile: {audio_file_path}", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    base64_audio, audio_format = utils.encode_audio_base64(audio_file_path)
    if not base64_audio:
        return {"status": "error", "message": f"Could not load or encode audio file: {audio_file_path}"}

    messages = [
        {"role": "system", "content": "You are an AI transcription service."},
        {"role": "user", "content": [
            {"type": "text", "text": "Transcribe the following audio."},
            {"type": "input_audio", "input_audio": {"data": base64_audio, "format": audio_format}}
        ]}
    ]
    transcription = _api_call_llm_for_vision_or_stt(client, messages, model="openai-audio") # Using openai-audio as per original
    if transcription:
        return {"status": "success", "transcription": transcription}
    else:
        return {"status": "error", "message": "Audio transcription failed."}

def generate_speech_audio(text_to_speak, voice="alloy", *, session, client, config, **kwargs): # client not used directly
    console.print(Panel(f"Tool: Generate Speech\nText: '{text_to_speak[:50]}...'\nVoice: {voice}", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    saved_path = _api_generate_speech_post(session, config.REFERRER_ID, text_to_speak, voice)
    if saved_path:
        return {"status": "success", "audio_file_path": saved_path, "message": f"Speech audio saved to {os.path.basename(saved_path)}"}
    else:
        return {"status": "error", "message": "Speech generation failed."}

def simple_web_search(url, *, session, client, config, **kwargs): # client not used directly
    console.print(Panel(f"Tool: Simple Web Search\nURL: [link={url}]{url}[/link]", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    try:
        if not url.startswith(('http://', 'https://')):
            return {"status": "error", "message": "Invalid URL. Must start with http:// or https://"}
        
        console.print(f"[grey50 i]Fetching {url}...[/grey50 i]")
        # Use the passed session which should have User-Agent and Referrer
        response = session.get(url, timeout=10) 
        response.raise_for_status()
        
        # Basic summary - real summarization would require another LLM call or parsing libraries
        content_summary = f"Successfully fetched content from {url}. Content length: {len(response.text)}. (Full content parsing not implemented in this simple tool)."
        # To get a real summary, you might want to use a library like BeautifulSoup to extract text
        # and then potentially pass it to another LLM call for summarization if it's too long.
        # For now, this is a placeholder summary.
        return {"status": "success", "url": url, "summary": content_summary, "message": f"Fetched content from {url}."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "url": url, "message": f"Failed to fetch URL {url}: {str(e)}"}
    except Exception as e: # Catch any other unexpected error
        return {"status": "error", "url": url, "message": f"An unexpected error occurred during web search for {url}: {str(e)}"}

def calculator(expression, *, session, client, config, **kwargs): # session, client, config not used
    console.print(Panel(f"Tool: Calculator\nExpression: '{expression}'", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    try:
        # Basic security: only allow specific characters.
        # This is a very rudimentary check and not foolproof for a production system.
        allowed_chars = "0123456789+-*/(). "
        if not all(char in allowed_chars for char in expression):
            raise ValueError("Expression contains disallowed characters.")
        
        # Prevent execution of arbitrary code by checking for alphabetic characters
        if any(c.isalpha() for c in expression):
            raise ValueError("Expression contains alphabetic characters and cannot be evaluated for security reasons.")

        # Using eval is generally risky, but with the character whitelist it's somewhat safer for this limited scope.
        # For a production system, a proper math expression parser would be better.
        result = eval(expression)
        return {"status": "success", "expression": expression, "result": str(result)}
    except Exception as e:
        return {"status": "error", "expression": expression, "message": f"Calculator error for expression '{expression}': {str(e)}"}