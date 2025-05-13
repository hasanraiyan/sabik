import requests
import os

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

def generate_speech_audio(text_to_speak, voice="alloy", *, session, client, config, **kwargs):
    console.print(Panel(f"Tool: Generate Speech\nText: '{text_to_speak[:50]}...'\nVoice: {voice}", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    saved_path = _api_generate_speech_post(session, config.REFERRER_ID, text_to_speak, voice)
    if saved_path:
        return {"status": "success", "audio_file_path": saved_path, "message": f"Speech audio saved to {os.path.basename(saved_path)}"}
    else:
        return {"status": "error", "message": "Speech generation failed."}
