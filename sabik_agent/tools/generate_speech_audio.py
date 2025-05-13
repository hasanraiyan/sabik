import requests
import os
import importlib.util
import subprocess
import platform
import base64
import tempfile
import webbrowser

from .. import utils
from ..interface import console, Panel
from ..config import OPENAI_BASE_URL_TEXT

def _convert_mp3_to_wav(mp3_path):
    """Convert an MP3 file to WAV format for better compatibility with playback methods."""
    try:
        # Check if pydub is installed, if not, try to install it
        if importlib.util.find_spec("pydub") is None:
            console.print(Panel("pydub not found. Attempting to install...", title="[bold yellow]Audio Conversion[/]", border_style="yellow"))
            try:
                subprocess.check_call(["pip", "install", "pydub"])
                console.print(Panel("pydub installed successfully", title="[bold green]Audio Conversion[/]", border_style="green"))
            except Exception as e:
                console.print(Panel(f"Failed to install pydub: {e}", title="[bold red]Audio Conversion Error[/]", border_style="red"))
                return None
        
        # Import pydub after ensuring it's installed
        from pydub import AudioSegment
        
        # Check if FFmpeg is available (required by pydub for MP3 conversion)
        try:
            # Try a simple FFmpeg command to check if it's installed
            ffmpeg_process = subprocess.Popen(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ffmpeg_process.communicate()
            if ffmpeg_process.returncode != 0:
                raise Exception("FFmpeg is not working properly")
        except (subprocess.SubprocessError, FileNotFoundError):
            console.print(Panel("FFmpeg not found. MP3 to WAV conversion requires FFmpeg to be installed.", 
                          title="[bold yellow]FFmpeg Missing[/]", border_style="yellow"))
            console.print(Panel("Please install FFmpeg: https://ffmpeg.org/download.html", 
                          title="[bold yellow]Installation Instructions[/]", border_style="yellow"))
            # Fall back to direct playback without conversion
            return None
        
        # Generate a temporary WAV file path
        wav_path = os.path.splitext(mp3_path)[0] + ".wav"
        
        # Convert MP3 to WAV
        sound = AudioSegment.from_mp3(mp3_path)
        sound.export(wav_path, format="wav")
        
        console.print(Panel(f"Converted MP3 to WAV: {os.path.basename(wav_path)}", title="[bold green]Audio Conversion[/]", border_style="green"))
        return wav_path
    except Exception as e:
        console.print(Panel(f"MP3 to WAV conversion error: {e}", title="[bold red]Audio Conversion Error[/]", border_style="red"))
        # Fall back to direct playback without conversion
        return None

def _play_audio_file(file_path):
    """Play an audio file using the appropriate method for the current platform."""
    try:
        system = platform.system()
        if system == "Windows":
            # For Windows, check file extension to determine best playback method
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == ".wav":
                # For WAV files, we can use winsound or Media.SoundPlayer
                try:
                    import winsound
                    winsound.PlaySound(file_path, winsound.SND_FILENAME)
                    return True
                except (ImportError, Exception) as e:
                    console.print(f"[yellow]Winsound playback failed: {e}[/yellow]")
            elif file_ext == ".mp3":
                # Try to convert MP3 to WAV first for better compatibility
                wav_path = _convert_mp3_to_wav(file_path)
                if wav_path:
                    try:
                        import winsound
                        winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                        return True
                    except (ImportError, Exception) as e:
                        console.print(f"[yellow]Winsound playback of converted WAV failed: {e}[/yellow]")
            
            # For MP3 or other formats, use the default system player
            # Media.SoundPlayer only supports WAV format, not MP3
            try:
                # Use the default system player via os.startfile
                os.startfile(file_path)
                return True
            except Exception as e:
                console.print(f"[yellow]Default player failed: {e}[/yellow]")
                
            # Try with PowerShell's Start-Process
            try:
                subprocess.Popen(["powershell", "-c", f"Start-Process '{file_path}'"])
                return True
            except Exception as e:
                console.print(f"[yellow]PowerShell playback failed: {e}[/yellow]")
                
            # Last resort: try with webbrowser module
            try:
                console.print(f"[yellow]Attempting to play audio with web browser...[/yellow]")
                # Convert to absolute file path with proper URI format
                file_uri = 'file:///' + os.path.abspath(file_path).replace('\\', '/')
                webbrowser.open(file_uri)
                return True
            except Exception as e:
                console.print(f"[yellow]Browser playback failed: {e}[/yellow]")
                return False
        elif system == "Darwin":  # macOS
            try:
                subprocess.Popen(["afplay", file_path])
                return True
            except Exception as e:
                console.print(f"[yellow]macOS afplay failed: {e}[/yellow]")
                # Try with webbrowser as fallback
                try:
                    console.print(f"[yellow]Attempting to play audio with web browser...[/yellow]")
                    file_uri = 'file://' + os.path.abspath(file_path)
                    webbrowser.open(file_uri)
                    return True
                except Exception as e:
                    console.print(f"[yellow]Browser playback failed: {e}[/yellow]")
                    return False
        elif system == "Linux":
            # Try with various Linux audio players
            success = False
            for player in ["aplay", "paplay", "mpg123", "mpg321"]:
                try:
                    subprocess.Popen([player, file_path])
                    success = True
                    break
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
            
            if success:
                return True
            
            # If all players failed, try with webbrowser as fallback
            try:
                console.print(f"[yellow]No suitable audio player found. Attempting to play audio with web browser...[/yellow]")
                file_uri = 'file://' + os.path.abspath(file_path)
                webbrowser.open(file_uri)
                return True
            except Exception as e:
                console.print(f"[yellow]Browser playback failed: {e}[/yellow]")
                return False
        else:
            console.print(Panel(f"Unsupported platform for audio playback: {system}", title="[bold yellow]Audio Playback[/]", border_style="yellow"))
            return False
    except Exception as e:
        console.print(Panel(f"Error playing audio: {e}", title="[bold red]Audio Playback Error[/]", border_style="red"))
        return False

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

def generate_speech_audio(text_to_speak, voice="alloy", *, session, client, config, auto_play=None, **kwargs):
    console.print(Panel(f"Tool: Generate Speech\nText: '{text_to_speak[:50]}...'\nVoice: {voice}", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    
    # Check if TTS is enabled in environment
    tts_enabled = os.environ.get("TTS_ENABLED", "true").lower() == "true"
    
    # Allow auto_play to be passed as a parameter, otherwise use environment variable
    if auto_play is None:
        auto_play = os.environ.get("TTS_AUTO_PLAY", "true").lower() == "true"
    
    if tts_enabled:
        # Try the primary OpenAI TTS method first
        saved_path = _api_generate_speech_post(session, config.REFERRER_ID, text_to_speak, voice)
        if saved_path:
            # Auto-play the audio if enabled
            if auto_play:
                console.print(Panel("Auto-playing generated audio...", title="[bold blue]Audio Playback[/]", border_style="blue"))
                
                # Check file extension for MP3 format
                file_ext = os.path.splitext(saved_path)[1].lower()
                if file_ext == ".mp3" and platform.system() == "Windows":
                    console.print(Panel("MP3 file detected on Windows. Attempting to convert to WAV for better playback compatibility...", 
                                  title="[bold blue]Audio Format[/]", border_style="blue"))
                    # Try to convert to WAV first for Windows compatibility
                    wav_path = _convert_mp3_to_wav(saved_path)
                    if wav_path:
                        play_success = _play_audio_file(wav_path)
                        if play_success:
                            play_status = "(auto-played WAV conversion)"
                            return {"status": "success", "audio_file_path": saved_path, 
                                    "wav_file_path": wav_path,
                                    "message": f"Speech audio saved to {os.path.basename(saved_path)} and converted to WAV for playback {play_status}"}
                
                # If no conversion or conversion failed, try playing the original file
                play_success = _play_audio_file(saved_path)
                play_status = "(auto-played)" if play_success else "(auto-play failed - try manual playback)"
                return {"status": "success", "audio_file_path": saved_path, "message": f"Speech audio saved to {os.path.basename(saved_path)} {play_status}"}
            return {"status": "success", "audio_file_path": saved_path, "message": f"Speech audio saved to {os.path.basename(saved_path)}"}
    
    # If TTS is disabled or the primary method failed, try the fallback
    console.print(Panel("Primary TTS method unavailable. Trying fallback with gTTS...", title="[bold yellow]TTS Fallback[/]", border_style="yellow"))
    fallback_path = _generate_speech_with_gtts(text_to_speak, voice)
    
    if fallback_path:
        # Auto-play the fallback audio if enabled
        if auto_play:
            console.print(Panel("Auto-playing generated audio (fallback)...", title="[bold blue]Audio Playback[/]", border_style="blue"))
            
            # Check file extension for MP3 format (gTTS generates MP3)
            if platform.system() == "Windows":
                console.print(Panel("MP3 file detected on Windows. Attempting to convert to WAV for better playback compatibility...", 
                              title="[bold blue]Audio Format[/]", border_style="blue"))
                # Try to convert to WAV first for Windows compatibility
                wav_path = _convert_mp3_to_wav(fallback_path)
                if wav_path:
                    play_success = _play_audio_file(wav_path)
                    if play_success:
                        play_status = "(auto-played WAV conversion)"
                        return {"status": "success", "audio_file_path": fallback_path, 
                                "wav_file_path": wav_path,
                                "message": f"Speech audio saved to {os.path.basename(fallback_path)} (using gTTS fallback) and converted to WAV for playback {play_status}"}
            
            # If no conversion or conversion failed, try playing the original file
            play_success = _play_audio_file(fallback_path)
            play_status = "(auto-played)" if play_success else "(auto-play failed - try manual playback)"
            return {"status": "success", "audio_file_path": fallback_path, "message": f"Speech audio saved to {os.path.basename(fallback_path)} (using gTTS fallback) {play_status}"}
        return {"status": "success", "audio_file_path": fallback_path, "message": f"Speech audio saved to {os.path.basename(fallback_path)} (using gTTS fallback)"}
    else:
        return {"status": "error", "message": "Speech generation failed with both primary and fallback methods."}
