from .. import utils
from ..interface import console, Panel

def _api_call_llm_for_vision_or_stt(client, messages, model):
    payload = {"model": model, "messages": messages, "stream": False}
    try:
        console.print(Panel(f"Model: {model}", title=f"[bold blue]Internal API Call: {model}[/]", border_style="blue", expand=False, width=80))
        response = client.chat.completions.create(**payload)
        if not response.choices:
            console.print("[red]Error: No choices from API.[/red]")
            return None
        content = response.choices[0].message.content
        console.print(Panel(f"{content[:150]}...", title="[bold green]Internal Result[/]", border_style="green", expand=False, width=80))
        return content
    except Exception as e:
        console.print(Panel(f"Error: {e}", title=f"[bold red]{model} API Error[/]", border_style="red"))
        return None

def transcribe_audio_file(audio_file_path, *, session, client, config, **kwargs):
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
    transcription = _api_call_llm_for_vision_or_stt(client, messages, model="openai-audio")
    if transcription:
        return {"status": "success", "transcription": transcription}
    else:
        return {"status": "error", "message": "Audio transcription failed."}
