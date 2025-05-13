import openai
import requests
import base64
import json
import os
import mimetypes
import time
import threading
import urllib.parse
from datetime import datetime
from PIL import Image
from io import BytesIO

# --- Rich Integration ---
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner 
from rich.text import Text

console = Console()

# --- Configuration ---
OPENAI_BASE_URL_TEXT = os.environ.get("OPENAI_BASE_URL_TEXT", "https://text.pollinations.ai/openai")
OPENAI_IMAGE_BASE_URL_TEXT = os.environ.get("OPENAI_IMAGE_BASE_URL_TEXT", "https://image.pollinations.ai")
REFERRER_ID = os.environ.get("OPENAI_REFERRER", "sabik")
API_KEY = os.environ.get("OPENAI_API_KEY", "dummy-openai-key")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "agent_outputs_tool_mode")

# --- Helper Functions ---
def encode_image_base64(image_path_or_url):
    try:
        if image_path_or_url.startswith(('http://', 'https://')):
            console.print(f"Fetching image: [link={image_path_or_url}]{image_path_or_url}[/link]")
            response = requests.get(image_path_or_url, timeout=15); response.raise_for_status()
            image_data = response.content; content_type = response.headers.get('Content-Type', 'image/jpeg')
        else:
            if not os.path.exists(image_path_or_url): raise FileNotFoundError(f"Image not found: {image_path_or_url}")
            console.print(f"Encoding image: [cyan]{image_path_or_url}[/cyan]")
            with open(image_path_or_url, "rb") as f: image_data = f.read()
            mime_type, _ = mimetypes.guess_type(image_path_or_url); content_type = mime_type or 'image/jpeg'
        try:
            img = Image.open(BytesIO(image_data)); img.verify()
            fmt_map = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'GIF': 'image/gif', 'WEBP': 'image/webp'}
            detected_mime = fmt_map.get(img.format);
            if detected_mime: content_type = detected_mime
            img.close()
        except Exception as img_err: console.print(f"[yellow]Warn:[/yellow] Pillow verify fail for '{image_path_or_url}'. Type: {content_type}. Err: {img_err}")
        return f"data:{content_type};base64,{base64.b64encode(image_data).decode('utf-8')}"
    except Exception as e: console.print(Panel(f"{e}", title="[bold red]Image Encode Error[/]", border_style="red")); return None

def encode_audio_base64(audio_path):
    try:
        if not os.path.exists(audio_path): raise FileNotFoundError(f"Audio not found: {audio_path}")
        console.print(f"Encoding audio: [cyan]{audio_path}[/cyan]")
        with open(audio_path, "rb") as f: audio_data = f.read()
        base64_audio = base64.b64encode(audio_data).decode('utf-8')
        audio_format = os.path.splitext(audio_path)[1].lower().lstrip('.')
        if not audio_format: console.print(f"[yellow]Warn:[/yellow] No audio format for {audio_path}. Assuming 'mp3'."); audio_format = 'mp3'
        return base64_audio, audio_format
    except Exception as e: console.print(Panel(f"{e}", title="[bold red]Audio Encode Error[/]", border_style="red")); return None, None

def save_base64_audio(base64_data, filename="output_audio.mp3"):
    try:
        audio_binary = base64.b64decode(base64_data); os.makedirs(OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'wb') as f: f.write(audio_binary)
        console.print(f"Audio saved: [bright_blue u]{filepath}[/bright_blue u]")
        return filepath
    except Exception as e: console.print(Panel(f"{e}", title="[bold red]Audio Save Error[/]", border_style="red")); return None

# --- Advanced Agent Class (Non-Streaming, Tool-Focused) ---
class AdvancedSabikAgent:
    def __init__(self, referrer=REFERRER_ID):
        self.referrer = referrer
        self.client = openai.OpenAI(
            base_url=OPENAI_BASE_URL_TEXT,
            api_key=API_KEY,
            default_headers={"Referer": self.referrer}
        )
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.referrer, "Referer": self.referrer})

        self.tools = [
            { "type": "function", "function": { "name": "generate_ai_image", "description": "Generate an image from a text prompt. Use when asked to create, draw, or visualize something.", "parameters": { "type": "object", "properties": { "prompt": {"type": "string", "description": "Detailed description of the image."}, "model": {"type": "string", "description": "Optional: Image model (e.g., 'flux', 'sdxl')."}, "width": {"type": "integer", "description": "Optional: Image width."}, "height": {"type": "integer", "description": "Optional: Image height."}, }, "required": ["prompt"]}}},
            { "type": "function", "function": { "name": "analyze_image_content", "description": "Analyzes an image (from URL or local path) to describe it or answer questions about it.", "parameters": { "type": "object", "properties": { "image_url_or_path": {"type": "string", "description": "URL or local path of the image."}, "analysis_prompt": {"type": "string", "description": "Specific question/focus for analysis (e.g., 'What color is the car?'). Defaults to general description."}, }, "required": ["image_url_or_path"]}}},
            { "type": "function", "function": { "name": "transcribe_audio_file", "description": "Transcribes speech from a local audio file into text.", "parameters": { "type": "object", "properties": { "audio_file_path": {"type": "string", "description": "Local path of the audio file."}, }, "required": ["audio_file_path"]}}},
            { "type": "function", "function": { "name": "generate_speech_audio", "description": "Converts text to speech audio and saves it. Use when asked to 'say', 'speak', or 'read aloud'.", "parameters": { "type": "object", "properties": { "text_to_speak": {"type": "string", "description": "Text to convert to speech."}, "voice": {"type": "string", "enum": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"], "description": "Voice for TTS. Defaults to 'alloy'."}, }, "required": ["text_to_speak"]}}},
            { "type": "function", "function": { "name": "simple_web_search", "description": "Fetches a summary of a single web page given its URL. Useful for finding current information or details from a specific website.", "parameters": { "type": "object", "properties": { "url": {"type": "string", "description": "The URL of the webpage to search/fetch."}, }, "required": ["url"]}}},
            { "type": "function", "function": { "name": "calculator", "description": "Evaluates a simple mathematical expression (e.g., '2+2', '100*3.14/2'). Use for calculations. Only supports basic arithmetic operations: +, -, *, / and parentheses.", "parameters": { "type": "object", "properties": { "expression": {"type": "string", "description": "The mathematical expression to evaluate."}, }, "required": ["expression"]}}},
        ]
        self.available_functions = {
            "generate_ai_image": self._tool_generate_image, "analyze_image_content": self._tool_analyze_image,
            "transcribe_audio_file": self._tool_transcribe_audio, "generate_speech_audio": self._tool_generate_speech,
            "simple_web_search": self._tool_simple_web_search, "calculator": self._tool_calculator,
        }
        self.message_history = []
        self.feed_threads = {}; self.stop_event = threading.Event()

    def _generate_image_get(self, prompt, model=None, width=None, height=None, seed=None, nologo=None, enhance=None, safe=None):
        params = {"model": model, "width": width, "height": height, "seed": seed, "nologo": nologo, "enhance": enhance, "safe": safe, "referrer": self.referrer}
        params = {k: v for k, v in params.items() if v is not None}
        encoded_prompt = urllib.parse.quote(prompt, safe=''); url = f"{OPENAI_IMAGE_BASE_URL_TEXT}/prompt/{encoded_prompt}"
        response = None
        try:
            console.print(Panel(f"Prompt: {prompt}\nModel: {model or 'default'}", title="[bold blue]API Call: GET Image[/]", border_style="blue", expand=False))
            response = self.session.get(url, params=params, timeout=300); response.raise_for_status()
            if 'image/' in response.headers.get('Content-Type', ''):
                os.makedirs(OUTPUT_DIR, exist_ok=True); safe_prompt = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in prompt[:40]).rstrip().replace(' ', '_');
                content_type = response.headers.get('Content-Type', 'image/jpeg'); ext = content_type.split('/')[-1].split(';')[0];
                if not ext or len(ext) > 5: ext = 'jpg'
                filename = f"image_{safe_prompt}_{int(time.time())}.{ext}"; filepath = os.path.join(OUTPUT_DIR, filename)
                with open(filepath, 'wb') as f: f.write(response.content)
                console.print(f"Image saved: [bright_blue u]{filepath}[/bright_blue u]")
                return response.url
            else: console.print(Panel(f"Expected image, got {response.headers.get('Content-Type')}\n{response.text[:200]}", title="[bold red]API Error[/]", border_style="red")); return None
        except requests.exceptions.Timeout: console.print(Panel("Timeout", title="[bold red]Timeout Error[/]", border_style="red")); return None
        except requests.exceptions.RequestException as e: console.print(Panel(f"Error: {e}\nStatus: {response.status_code if response else 'N/A'}", title="[bold red]Request Error[/]", border_style="red")); return None
        except Exception as e: console.print(Panel(f"Save Error: {e}", title="[bold red]Save Error[/]", border_style="red")); return None

    def _generate_speech_post(self, text, voice="alloy"):
        payload = {"model": "openai-audio", "messages": [{"role": "user", "content": text}], "voice": voice, "referrer": self.referrer}
        url = OPENAI_BASE_URL_TEXT; response = None
        try:
            console.print(Panel(f"Text: {text[:50]}...\nVoice: {voice}", title="[bold blue]API Call: POST TTS[/]", border_style="blue", expand=False))
            response = self.session.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=120); response.raise_for_status(); response_data = response.json()
            audio_base64 = response_data.get('choices', [{}])[0].get('message', {}).get('audio', {}).get('data')
            if not audio_base64 or not isinstance(audio_base64, str): raise ValueError(f"No audio data: {response.text[:200]}")
            safe_text = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in text[:30]).rstrip().replace(' ', '_'); filename = f"speech_{safe_text}_{voice}_{int(time.time())}.mp3"
            return save_base64_audio(audio_base64, filename)
        except requests.exceptions.RequestException as e: console.print(Panel(f"Error: {e}\nStatus: {response.status_code if response else 'N/A'}", title="[bold red]Request Error[/]", border_style="red")); return None
        except (KeyError, IndexError, TypeError, ValueError) as e: console.print(Panel(f"Parse Error: {e}\nResp: {response.text[:200] if response else 'N/A'}", title="[bold red]Parse Error[/]", border_style="red")); return None
        except Exception as e: console.print(Panel(f"TTS Error: {e}", title="[bold red]TTS Error[/]", border_style="red")); return None

    def _call_llm_for_vision_or_stt(self, messages, model):
         payload = {"model": model, "messages": messages, "stream": False}
         try:
            console.print(Panel(f"Model: {model}", title=f"[bold blue]Internal API Call: {model}[/]", border_style="blue", expand=False, width=80))
            response = self.client.chat.completions.create(**payload)
            if not response.choices: console.print("[red]Error: No choices from API.[/red]"); return None
            content = response.choices[0].message.content
            console.print(Panel(f"{content[:150]}...", title="[bold green]Internal Result[/]", border_style="green", expand=False, width=80))
            return content
         except Exception as e: console.print(Panel(f"Error: {e}", title=f"[bold red]{model} API Error[/]", border_style="red")); return None

    def _tool_generate_image(self, prompt, model=None, width=None, height=None, seed=None, nologo=None):
        console.print(Panel(f"Tool: Generate Image\nPrompt: '{prompt}'", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
        image_url = self._generate_image_get(prompt=prompt, model=model, width=width, height=height, seed=seed, nologo=nologo)
        return {"status": "success", "image_url": image_url, "message": f"Image generated: {image_url}"} if image_url else {"status": "error", "message": f"Failed to generate image for '{prompt}'."}

    def _tool_analyze_image(self, image_url_or_path, analysis_prompt="Describe the image in detail."):
         console.print(Panel(f"Tool: Analyze Image\nSource: {image_url_or_path}\nPrompt: '{analysis_prompt}'", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
         base64_image_data = encode_image_base64(image_url_or_path)
         if not base64_image_data: return {"status": "error", "message": f"Could not load/encode: {image_url_or_path}"}
         messages = [{"role": "system", "content": "You are an AI vision expert."}, {"role": "user", "content": [{"type": "text", "text": analysis_prompt}, {"type": "image_url", "image_url": {"url": base64_image_data}}]}]
         analysis = self._call_llm_for_vision_or_stt(messages, model="openai-large")
         return {"status": "success", "analysis": analysis} if analysis else {"status": "error", "message": "Image analysis failed."}

    def _tool_transcribe_audio(self, audio_file_path):
        console.print(Panel(f"Tool: Transcribe Audio\nFile: {audio_file_path}", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
        base64_audio, audio_format = encode_audio_base64(audio_file_path)
        if not base64_audio: return {"status": "error", "message": f"Could not load/encode: {audio_file_path}"}
        messages = [{"role": "system", "content": "You are an AI transcription service."}, {"role": "user", "content": [{"type": "text", "text": "Transcribe."}, {"type": "input_audio", "input_audio": {"data": base64_audio, "format": audio_format}}]}]
        transcription = self._call_llm_for_vision_or_stt(messages, model="openai-audio")
        return {"status": "success", "transcription": transcription} if transcription else {"status": "error", "message": "Transcription failed."}

    def _tool_generate_speech(self, text_to_speak, voice="alloy"):
         console.print(Panel(f"Tool: Generate Speech\nText: '{text_to_speak[:50]}...'\nVoice: {voice}", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
         saved_path = self._generate_speech_post(text_to_speak, voice)
         return {"status": "success", "audio_file_path": saved_path, "message": f"Speech saved to {os.path.basename(saved_path) if saved_path else 'N/A'}"} if saved_path else {"status": "error", "message": "Speech generation failed."}

    def _tool_simple_web_search(self, url):
        console.print(Panel(f"Tool: Simple Web Search\nURL: [link={url}]{url}[/link]", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
        try:
            if not url.startswith(('http://', 'https://')): return {"status": "error", "message": "Invalid URL. Must start with http(s)://"}
            console.print(f"[grey50 i]Fetching {url}...[/grey50 i]")
            headers = {'User-Agent': 'MyAdvancedToolAgent/1.0 (WebSearchTool)'}
            response = requests.get(url, timeout=10, headers=headers); response.raise_for_status()
            content_summary = f"Successfully fetched {url}. Content length: {len(response.text)}. (Full content parsing not implemented in this demo)."
            return {"status": "success", "url": url, "summary": content_summary, "message": f"Fetched content from {url}."}
        except requests.exceptions.RequestException as e: return {"status": "error", "url": url, "message": f"Failed to fetch URL {url}: {e}"}
        except Exception as e: return {"status": "error", "url": url, "message": f"Web search error: {e}"}

    def _tool_calculator(self, expression):
        console.print(Panel(f"Tool: Calculator\nExpression: '{expression}'", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
        try:
            allowed_chars = "0123456789+-*/(). "
            if not all(char in allowed_chars for char in expression): raise ValueError("Expression contains disallowed characters.")
            if any(c.isalpha() for c in expression): raise ValueError("Expression contains alphabetic characters.")
            result = eval(expression) 
            return {"status": "success", "expression": expression, "result": str(result)}
        except Exception as e:
            return {"status": "error", "expression": expression, "message": f"Calculator error for '{expression}': {e}"}

    def _chat_completion_with_tools(self, messages_to_send, model="openai-large"):
        current_messages_for_api_call = list(messages_to_send)
        request_payload = {"model": model, "messages": current_messages_for_api_call, "stream": False, "tools": self.tools, "tool_choice": "auto"}

        console.print(Panel(f"Model: {model}, Tools: Enabled", title="[bold blue]Sending to LLM[/]", border_style="blue", expand=False))
        spinner_text = Text("Assistant is thinking...", style="grey50 italic")
        spinner_obj = Spinner("dots", text=spinner_text)
        live_renderable = Panel(spinner_obj, border_style="dim grey50", expand=False)

        with Live(live_renderable, console=console, refresh_per_second=10, vertical_overflow="visible") as live:
            try:
                response = self.client.chat.completions.create(**request_payload)
            except Exception as e:
                live.update(Panel(f"API Call Failed: {e}", title="[bold red]Error[/]", border_style="red")); console.print(f"[red]Initial API call error: {e}[/red]"); return None

            if not response.choices:
                live.update(Panel("No response choices from API.", title="[bold red]Error[/]", border_style="red")); console.print("[red]Error: No choices from API.[/red]"); return None
            
            response_message_pydantic = response.choices[0].message # This is the Pydantic model object
            response_message_dict = response_message_pydantic.model_dump() # This is a dict
            self.message_history.append(response_message_dict) # Add assistant's first response (which might contain tool_calls)

            loop_count = 0; max_loops = 5
            # IMPORTANT: Check tool_calls on the dictionary version for the loop condition
            while response_message_dict.get("tool_calls") and loop_count < max_loops:
                loop_count += 1
                
                live.update(Panel(f"Assistant requested tool call(s)... (Loop {loop_count})", title="[bold magenta]Tool Call Requested[/]", border_style="magenta"))
                tool_calls_display = []
                # Iterate over the list of tool_call dicts
                for tc_dict in response_message_dict.get("tool_calls", []): 
                    tool_calls_display.append(f"  ID: {tc_dict.get('id')}, Func: {tc_dict.get('function',{}).get('name')}, Args: {tc_dict.get('function',{}).get('arguments')}")
                console.print(Panel("\n".join(tool_calls_display), title="[bold bright_yellow]Tool Call Details[/]", border_style="bright_yellow"))

                # Pass the list of tool_call dictionaries from response_message_dict
                tool_results = self._handle_function_call(response_message_dict.get("tool_calls", []))
                
                for res_dict in tool_results: # tool_results is a list of dicts
                    self.message_history.append(res_dict)

                live.update(Panel(f"Sending tool results to LLM... (Loop {loop_count})", title="[bold blue]Follow-up LLM Call[/]", border_style="blue"))
                follow_up_payload = {"model": model, "messages": list(self.message_history), "stream": False, "tools": self.tools, "tool_choice": "auto"}
                
                try:
                    response = self.client.chat.completions.create(**follow_up_payload)
                except Exception as e:
                    live.update(Panel(f"API Call Failed (Follow-up): {e}", title="[bold red]Error[/]", border_style="red")); console.print(f"[red]Follow-up API call error: {e}[/red]"); return None

                if not response.choices:
                    live.update(Panel("No response after tool call.", title="[bold red]Error[/]", border_style="red")); console.print("[red]Error: No choices after tool call.[/red]"); return None
                
                response_message_pydantic = response.choices[0].message # New Pydantic object
                response_message_dict = response_message_pydantic.model_dump() # Convert to dict for next loop & history
                self.message_history.append(response_message_dict)

            if loop_count >= max_loops: live.update(Panel(f"Max loops ({max_loops}) reached.", title="[bold orange]Loop Limit[/]", border_style="orange")); console.print(f"[orange]Warn: Max tool loops.[/orange]")

            # Use the *latest* response_message_pydantic object for final content
            final_content = response_message_pydantic.content 
            if final_content:
                live.update(Panel(Markdown(final_content), title="[bold bright_magenta]Assistant[/]", border_style="bright_magenta", title_align="left"))
            else:
                live.update(Panel("[No text content in final response. Review tool outputs.]", title="[bold bright_magenta]Assistant[/]", border_style="bright_magenta", title_align="left"))
            
            return response_message_pydantic.model_dump() # Return the dict of the final message


    def _handle_function_call(self, tool_calls_list_of_dicts): 
        tool_results_for_history = [] 
        table = Table(title="[bold yellow]Executing Tools[/]", show_lines=True, expand=False)
        table.add_column("ID", style="dim", overflow="fold")
        table.add_column("Function", style="cyan", overflow="fold")
        table.add_column("Arguments", style="magenta", overflow="fold", max_width=50)
        table.add_column("Status", style="green", overflow="fold")

        if not tool_calls_list_of_dicts: 
            return tool_results_for_history

        for tool_call_dict in tool_calls_list_of_dicts: 
            function_dict = tool_call_dict.get("function", {})
            function_name = function_dict.get("name")
            args_str = function_dict.get("arguments")
            tool_call_id = tool_call_dict.get("id")
            
            status_display = "[red]Error[/red]"
            tool_output_content_str = "" 

            if function_to_call := self.available_functions.get(str(function_name)): # Ensure function_name is str
                if args_str is not None and tool_call_id is not None:
                    try:
                        function_args = json.loads(args_str)
                        function_response_obj = function_to_call(**function_args) 

                        if isinstance(function_response_obj, dict):
                            tool_output_content_str = json.dumps(function_response_obj) 
                            status_display = f"[green]{function_response_obj.get('status', 'unknown').capitalize()}[/green]"
                            console.print(Panel(Syntax(json.dumps(function_response_obj, indent=2), "json", theme="default", word_wrap=True), title=f"Result: [cyan]{function_name}[/]", border_style="green", expand=False))
                        else: 
                            tool_output_content_str = str(function_response_obj)
                            status_display = "[yellow]Non-dict tool result[/yellow]"
                            console.print(f"[yellow]Warning:[/yellow] Tool {function_name} returned non-dict: {tool_output_content_str}")
                    except json.JSONDecodeError as e:
                        tool_output_content_str = json.dumps({"error": f"Invalid JSON arguments for tool '{function_name}': {str(e)}", "args_received": args_str})
                        console.print(Panel(f"Invalid JSON args for {function_name}: {args_str}\n{e}", title="[bold red]Tool Arg Error[/]", border_style="red"))
                    except TypeError as e:
                        tool_output_content_str = json.dumps({"error": f"Incorrect arguments calling tool '{function_name}': {str(e)}", "args_received": args_str})
                        console.print(Panel(f"Incorrect args for {function_name} with {args_str}:\n{e}", title="[bold red]Tool Call Error[/]", border_style="red"))
                    except Exception as e:
                        tool_output_content_str = json.dumps({"error": f"Exception executing tool '{function_name}': {str(e)}", "args_received": args_str})
                        console.print(Panel(f"Error executing {function_name}:\n{type(e).__name__}: {e}", title="[bold red]Tool Exec Error[/]", border_style="red"))
                else: # Missing args_str or tool_call_id
                    tool_output_content_str = json.dumps({"error": f"Malformed tool_call object for function '{function_name}'. Missing arguments or ID."})
                    console.print(Panel(f"Malformed tool_call for '{function_name}': {tool_call_dict}", title="[bold red]Malformed Tool Call[/]", border_style="red"))
            else: # Function not found
                 tool_output_content_str = json.dumps({"error": f"Function '{function_name}' not found by agent."})
                 console.print(Panel(f"Model requested unknown function '{function_name}'", title="[bold red]Unknown Tool[/]", border_style="red"))
                 status_display = "[red]Unknown Function[/red]"
            
            table.add_row(str(tool_call_id), str(function_name), str(args_str), status_display)
            tool_results_for_history.append({ 
                "tool_call_id": str(tool_call_id), 
                "role": "tool",
                "name": str(function_name), 
                "content": tool_output_content_str 
            })
        console.print(table)
        return tool_results_for_history

    def process_input(self, user_input):
        self.message_history.append({"role": "user", "content": user_input})
        model = "openai-large"
        console.rule("[bold blue]Processing Request[/]")
        messages_to_send = list(self.message_history)
        assistant_response_dict = self._chat_completion_with_tools(messages_to_send, model=model)
        if assistant_response_dict:
            return assistant_response_dict.get("content", "[No text content or was tool sequence]")
        else:
            return "[Agent Info: Failed to get response after processing.]"

    def _monitor_feed(self, feed_url, feed_name):
        console.print(Panel(f"Starting Monitor: {threading.current_thread().name}", title=f"[bold green]{feed_name} Monitor[/]", border_style="green"))
        while not self.stop_event.is_set():
            try:
                response = self.session.get(feed_url, stream=True, headers={'Accept': 'text/event-stream'}, timeout=(10, 60))
                response.raise_for_status(); client = sseclient.SSEClient(response)
                console.print(f"[green dim]{feed_name} connected.[/green dim]")
                for event in client.events():
                    if self.stop_event.is_set(): break
                    if event.data:
                        ts = datetime.now().strftime("%H:%M:%S")
                        console.rule(style="dim cyan");
                        try:
                            data = json.loads(event.data)
                            syntax = Syntax(json.dumps(data, indent=2), "json", theme="default", line_numbers=False, word_wrap=True)
                            console.print(Panel(syntax, title=f"[cyan]{feed_name} Event ({ts})[/]", border_style="cyan"))
                        except json.JSONDecodeError:
                            if event.data.strip() and not event.data.startswith(':'): console.print(Panel(event.data, title=f"[yellow]{feed_name} Raw ({ts})[/]", border_style="yellow"))
                if not self.stop_event.is_set(): console.print(f"[yellow dim]{feed_name} stream ended. Retrying...[/yellow dim]"); time.sleep(5)
            except requests.exceptions.Timeout: console.print(f"[yellow dim]{feed_name} timeout. Retrying...[/yellow dim]"); time.sleep(10)
            except requests.exceptions.RequestException as e: console.print(f"[yellow dim]{feed_name} error: {e}. Retrying...[/yellow dim]"); time.sleep(10)
            except Exception as e: console.print(f"[yellow dim]Error in {feed_name}: {type(e).__name__}. Retrying...[/yellow dim]"); time.sleep(10)
            if self.stop_event.is_set(): break
        console.print(Panel(f"Exited: {threading.current_thread().name}", title=f"[bold red]{feed_name} Monitor Stopped[/]", border_style="red"))

    def start_image_feed_monitor(self):
        feed_key="image_feed"; url=f"{OPENAI_IMAGE_BASE_URL_TEXT}/feed"
        if feed_key not in self.feed_threads or not self.feed_threads[feed_key].is_alive():
            t=threading.Thread(target=self._monitor_feed,args=(url,"Image Feed"),daemon=True,name="ImgFeed");self.feed_threads[feed_key]=t;t.start();console.print("[green]Image monitor started.[/green]");return True
        else:console.print("[yellow]Image monitor running.[/yellow]");return False
    def start_text_feed_monitor(self):
        feed_key="text_feed";p=urllib.parse.urlparse(OPENAI_BASE_URL_TEXT);b=f"{p.scheme}://{p.netloc}";url=f"{b}/feed"
        if feed_key not in self.feed_threads or not self.feed_threads[feed_key].is_alive():
            t=threading.Thread(target=self._monitor_feed,args=(url,"Text Feed"),daemon=True,name="TxtFeed");self.feed_threads[feed_key]=t;t.start();console.print("[green]Text monitor started.[/green]");return True
        else:console.print("[yellow]Text monitor running.[/yellow]");return False
    def stop_all_monitors(self):
        if not self.feed_threads:return
        console.print("[bold yellow]Stopping monitors...[/]");self.stop_event.set();
        for t in list(self.feed_threads.values()):
            if t.is_alive():t.join(timeout=5)
        self.feed_threads={};self.stop_event.clear();console.print("[bold red]Monitors stopped.[/]")

# --- Main Execution Example ---
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    agent = AdvancedSabikAgent()
    console.print(Panel(f"""[bold]Sabik AI[/]
Referrer: [cyan]{agent.referrer}[/cyan]
LLM uses tools. Responses not streamed.""",title="[bold green]Welcome![/]",border_style="green",expand=False))
    console.print(Panel("""[bold]How to Use:[/bold]
  - Ask agent tasks using natural language. Examples:
    - "Generate an image of a serene beach at dawn."
    - "What's in the picture at ./my_image.jpg? Is there a dog?"
    - "Transcribe the audio from meeting_notes.wav."
    - "Say 'Good morning!' with an echo voice."
    - "What is the capital of France?"
    - "Calculate (100 / 5) * 2 + 7"
  - [cyan]monitor image [start|stop][/cyan]
  - [cyan]monitor text [start|stop][/cyan]
  - [cyan]quit[/cyan] or [cyan]exit[/cyan]""",title="Help",border_style="blue",expand=False))
    try:
        while True:
            try: user_input = console.input("[bold chart_reuse]You> [/bold chart_reuse]")
            except EOFError: console.print("\nExiting..."); break
            except KeyboardInterrupt: console.print("\nExiting..."); break
            command = user_input.lower().strip()
            if command in ["quit", "exit"]: console.print("Exiting..."); break
            elif command == "monitor image start": agent.start_image_feed_monitor(); continue
            elif command == "monitor image stop": agent.stop_all_monitors(); continue
            elif command == "monitor text start": agent.start_text_feed_monitor(); continue
            elif command == "monitor text stop": agent.stop_all_monitors(); continue
            if not command: continue
            final_response_content = agent.process_input(user_input)
            if final_response_content and final_response_content.startswith("[Agent Info:"):
                 console.print(f"[yellow]{final_response_content}[/yellow]")
            console.rule(style="dim grey50")
    finally:
         agent.stop_all_monitors()
         console.print("[bold]Agent shut down gracefully.[/bold]")