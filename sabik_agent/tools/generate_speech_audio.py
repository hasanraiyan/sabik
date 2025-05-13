import requests
import os
import importlib.util

from .. import utils
from ..interface import console, Panel
from ..config import OPENAI_BASE_URL_TEXT

def _api_generate_speech_post(session, referrer, text, voice="alloy"):
    payload = {
        "model": "openai-audio",
        "messages": [{"role": "user", "content": text}],
        "voice": voice,
        "referrer": referrer
    }
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
        filename = f"speech_{safe_text}_{voice}_{int(os.path.getmtime(__file__))}.mp3"
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

def _generate_speech_with_gtts(text, voice="en"):
    # Check if gtts is installed, if not, try to install it
    if importlib.util.find_spec("gtts") is None:
        console.print(Panel("gTTS not found. Attempting to install...", title="[bold yellow]TTS Fallback[/]", border_style="yellow"))
        try:
            import subprocess
            subprocess.check_call(["pip", "install", "gtts"])
            console.print(Panel("gTTS installed successfully", title="[bold green]TTS Fallback[/]", border_style="green"))
        except Exception as e:
            console.print(Panel(f"Failed to install gTTS: {e}", title="[bold red]TTS Fallback Error[/]", border_style="red"))
            return None
    
    try:
        from gtts import gTTS
        # Map OpenAI voices to language codes for gTTS
        voice_to_lang = {
            "alloy": "en",
            "echo": "en",
            "fable": "en",
            "onyx": "en",
            "nova": "en",
            "shimmer": "en"
        }
        lang = voice_to_lang.get(voice, "en")
        
        # Create gTTS object
        tts = gTTS(text=text, lang=lang, slow=False)
        
        # Generate a filename
        safe_text = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in text[:30]).rstrip().replace(' ', '_')
        filename = f"speech_{safe_text}_{voice}_{int(os.path.getmtime(__file__))}.mp3"
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..", "outputs", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save the audio file
        tts.save(filepath)
        console.print(Panel(f"Generated speech with gTTS: {filename}", title="[bold green]TTS Fallback Success[/]", border_style="green"))
        return filepath
    except Exception as e:
        console.print(Panel(f"gTTS generation error: {e}", title="[bold red]TTS Fallback Error[/]", border_style="red"))
        return None

def generate_speech_audio(text_to_speak, voice="alloy", *, session, client, config, **kwargs):
    console.print(Panel(f"Tool: Generate Speech\nText: '{text_to_speak[:50]}...'\nVoice: {voice}", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    
    # Check if TTS is enabled in environment
    tts_enabled = os.environ.get("TTS_ENABLED", "true").lower() == "true"
    
    if tts_enabled:
        # Try the primary OpenAI TTS method first
        saved_path = _api_generate_speech_post(session, config.REFERRER_ID, text_to_speak, voice)
        if saved_path:
            return {"status": "success", "audio_file_path": saved_path, "message": f"Speech audio saved to {os.path.basename(saved_path)}"}
    
    # If TTS is disabled or the primary method failed, try the fallback
    console.print(Panel("Primary TTS method unavailable. Trying fallback with gTTS...", title="[bold yellow]TTS Fallback[/]", border_style="yellow"))
    fallback_path = _generate_speech_with_gtts(text_to_speak, voice)
    
    if fallback_path:
        return {"status": "success", "audio_file_path": fallback_path, "message": f"Speech audio saved to {os.path.basename(fallback_path)} (using gTTS fallback)"}
    else:
        return {"status": "error", "message": "Speech generation failed with both primary and fallback methods."}
