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

def analyze_image_content(image_url_or_path, analysis_prompt="Describe the image in detail.", *, session, client, config, **kwargs):
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
    analysis = _api_call_llm_for_vision_or_stt(client, messages, model="openai-large")
    if analysis:
        return {"status": "success", "analysis": analysis}
    else:
        return {"status": "error", "message": "Image analysis failed using the vision model."}
