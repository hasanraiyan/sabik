# sabik_agent/agent.py
import openai
import requests
import json
import os # For API_KEY, etc., if not using config module directly for everything
import time # For loop counts, etc.
# urllib.parse removed as tool helpers handle URL encoding

# Rich components for agent's own logging/display if needed outside of tools
from .interface import console, Panel, Markdown, Live, Spinner, Text, Syntax, Table

# Agent-specific modules
from . import config as app_config # Use the config module
from . import tools as agent_tools
# from . import utils - tools will import utils directly or agent passes utils module to tools

class AdvancedSabikAgent:
    def __init__(self, referrer=None):
        """
        Initialize Sabik AI assistant with core values:
        - Speed: respond with maximum efficiency
        - Control: execute tasks cleanly, with no unnecessary fluff
        - Focus: keep all answers concise, relevant, and context-aware
        - Consistency: maintain system instructions throughout processing
        """
        self.referrer = referrer or app_config.REFERRER_ID
        self.client = openai.OpenAI(
            base_url=app_config.OPENAI_BASE_URL_TEXT,
            api_key=app_config.API_KEY,
            default_headers={"Referer": self.referrer}
        )
        self.system_instructions = """
        You are Sabik, a terminal-first AI assistant. You are fast, focused, and efficient—built for power users who operate in the command line.

Your core values are:
- Speed: respond with maximum efficiency.
- Control: execute tasks cleanly, with no unnecessary fluff.
- Focus: keep all answers concise, relevant, and context-aware.

Guidelines:
1. Never break character. You are not a chatbot. You are a terminal AI assistant.
2. Minimize verbosity. Do not provide excessive explanations unless explicitly asked.
3. Avoid follow-up questions unless clarification is absolutely necessary. Prefer immediate execution.
4. When unsure, clearly say so and recommend a next step.
5. Always prefer actionable output—code, commands, summaries, or results—over vague or conversational replies.
6. Respect user privacy. Do not log or retain information beyond the current session.
7. Avoid emotional tone, chit-chat, or overly friendly phrasing. You are a productivity tool.

Your job is to help the user execute tasks quickly and intelligently from the terminal using natural language.

Stay sharp. Stay quiet unless needed. Let the user lead.

You are Sabik.
"""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.referrer, "Referer": self.referrer})

        # Tool definitions (schemas)
        self.tools_schemas = [
            { "type": "function", "function": { "name": "generate_ai_image", "description": "Generate an image from a text prompt. Use when asked to create, draw, or visualize something.", "parameters": { "type": "object", "properties": { "prompt": {"type": "string", "description": "Detailed description of the image."}, "model": {"type": "string", "description": "Optional: Image model (e.g., 'flux', 'turbo')."}, "width": {"type": "integer", "description": "Optional: Image width."}, "height": {"type": "integer", "description": "Optional: Image height."}, }, "required": ["prompt"]}}},
            { "type": "function", "function": { "name": "analyze_image_content", "description": "Analyzes an image (from URL or local path) to describe it or answer questions about it.", "parameters": { "type": "object", "properties": { "image_url_or_path": {"type": "string", "description": "URL or local path of the image."}, "analysis_prompt": {"type": "string", "description": "Specific question/focus for analysis (e.g., 'What color is the car?'). Defaults to general description."}, }, "required": ["image_url_or_path"]}}},
            { "type": "function", "function": { "name": "transcribe_audio_file", "description": "Transcribes speech from a local audio file into text.", "parameters": { "type": "object", "properties": { "audio_file_path": {"type": "string", "description": "Local path of the audio file."}, }, "required": ["audio_file_path"]}}},
            { "type": "function", "function": { "name": "generate_speech_audio", "description": "Converts text to speech audio, saves it, and automatically plays it. Use when asked to 'say', 'speak', or 'read aloud'.", "parameters": { "type": "object", "properties": { "text_to_speak": {"type": "string", "description": "Text to convert to speech."}, "voice": {"type": "string", "enum": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"], "description": "Voice for TTS. Defaults to 'alloy'."}, "auto_play": {"type": "boolean", "description": "Whether to automatically play the audio after generation. Defaults to true."} }, "required": ["text_to_speak"]}}},
            { "type": "function", "function": { "name": "simple_web_search", "description": "Fetches a summary of a single web page given its URL. Useful for finding current information or details from a specific website.", "parameters": { "type": "object", "properties": { "url": {"type": "string", "description": "The URL of the webpage to search/fetch."}, }, "required": ["url"]}}},
            { "type": "function", "function": { "name": "calculator", "description": "Evaluates a simple mathematical expression (e.g., '2+2', '100*3.14/2'). Use for calculations. Only supports basic arithmetic operations: +, -, *, / and parentheses.", "parameters": { "type": "object", "properties": { "expression": {"type": "string", "description": "The mathematical expression to evaluate."}, }, "required": ["expression"]}}},
        ]
        
        # Mapping tool names to their actual functions in agent_tools module
        self.available_functions = {
            "generate_ai_image": agent_tools.generate_ai_image,
            "analyze_image_content": agent_tools.analyze_image_content,
            "transcribe_audio_file": agent_tools.transcribe_audio_file,
            "generate_speech_audio": agent_tools.generate_speech_audio,
            "simple_web_search": agent_tools.simple_web_search,
            "calculator": agent_tools.calculator,
        }
        self.message_history = []

    def _chat_completion_with_tools(self, messages_to_send, model="openai-large"):
        current_messages_for_api_call = list(messages_to_send) # Work with a copy
        request_payload = {
            "model": model,
            "messages": current_messages_for_api_call,
            "stream": False,
            "tools": self.tools_schemas, # Use the schemas here
            "tool_choice": "auto"
        }

        console.print(Panel(f"Model: {model}, Tools: Enabled", title="[bold blue]Sending to LLM[/]", border_style="blue", expand=False))
        spinner_text = Text("Assistant is thinking...", style="grey50 italic")
        spinner_obj = Spinner("dots", text=spinner_text)
        live_renderable = Panel(spinner_obj, border_style="dim grey50", expand=False)

        with Live(live_renderable, console=console, refresh_per_second=10, vertical_overflow="visible") as live:
            try:
                response = self.client.chat.completions.create(**request_payload)
            except Exception as e:
                live.update(Panel(f"API Call Failed: {str(e)}", title="[bold red]Error[/]", border_style="red"))
                console.print(f"[red]Initial API call error: {e}[/red]")
                return None

            if not response.choices:
                live.update(Panel("No response choices from API.", title="[bold red]Error[/]", border_style="red"))
                console.print("[red]Error: No choices from API.[/red]")
                return None
            
            response_message_pydantic = response.choices[0].message
            response_message_dict = response_message_pydantic.model_dump(exclude_unset=True) # Get as dict
            self.message_history.append(response_message_dict) # Add assistant's first response

            loop_count = 0
            max_loops = 5 # Max tool call iterations
            
            # Loop as long as the LLM requests tool calls
            while response_message_dict.get("tool_calls") and loop_count < max_loops:
                loop_count += 1
                live.update(Panel(f"Assistant requested tool call(s)... (Iteration {loop_count})", title="[bold magenta]Tool Call Requested[/]", border_style="magenta"))
                
                tool_calls_display = []
                for tc_dict in response_message_dict.get("tool_calls", []):
                    func_info = tc_dict.get('function', {})
                    tool_calls_display.append(f"  ID: {tc_dict.get('id')}, Func: {func_info.get('name')}, Args: {func_info.get('arguments')}")
                console.print(Panel("\n".join(tool_calls_display), title="[bold bright_yellow]Tool Call Details[/]", border_style="bright_yellow"))

                # Handle the function calls and get results
                # The tool_calls from Pydantic model are already dict-like
                tool_results = self._handle_function_call(response_message_dict.get("tool_calls", []))
                
                # Add tool results to message history for the next LLM call
                for res_dict in tool_results:
                    self.message_history.append(res_dict)

                live.update(Panel(f"Sending tool results to LLM... (Iteration {loop_count})", title="[bold blue]Follow-up LLM Call[/]", border_style="blue"))
                
                # Make a new call to the LLM with the tool results
                follow_up_payload = {
                    "model": model,
                    "messages": list(self.message_history), # Send the updated history
                    "stream": False,
                    "tools": self.tools_schemas,
                    "tool_choice": "auto"
                }
                
                try:
                    response = self.client.chat.completions.create(**follow_up_payload)
                except Exception as e:
                    live.update(Panel(f"API Call Failed (Follow-up): {str(e)}", title="[bold red]Error[/]", border_style="red"))
                    console.print(f"[red]Follow-up API call error: {e}[/red]")
                    return None

                if not response.choices:
                    live.update(Panel("No response choices after tool call.", title="[bold red]Error[/]", border_style="red"))
                    console.print("[red]Error: No choices after tool call.[/red]")
                    return None
                
                response_message_pydantic = response.choices[0].message
                response_message_dict = response_message_pydantic.model_dump(exclude_unset=True)
                self.message_history.append(response_message_dict) # Add new assistant response

            if loop_count >= max_loops:
                live.update(Panel(f"Max tool call iterations ({max_loops}) reached.", title="[bold orange]Loop Limit[/]", border_style="orange"))
                console.print(f"[orange3]Warning: Max tool call iterations reached.[/orange3]")

            final_content = response_message_pydantic.content
            if final_content:
                live.update(Panel(Markdown(final_content), title="[bold bright_magenta]Assistant[/]", border_style="bright_magenta", title_align="left"))
            else: # If the last message was a tool call, there might be no text content
                live.update(Panel("[No direct text content in final assistant response. Review tool outputs and logs.]", title="[bold bright_magenta]Assistant[/]", border_style="bright_magenta", title_align="left"))
            
            return response_message_dict # Return the dictionary of the final assistant message

    def _handle_function_call(self, tool_calls_list_of_dicts):
        tool_results_for_history = []
        
        table = Table(title="[bold yellow]Executing Tools[/]", show_lines=True, expand=False)
        table.add_column("Tool ID", style="dim", overflow="fold")
        table.add_column("Function", style="cyan", overflow="fold")
        table.add_column("Arguments", style="magenta", overflow="fold", max_width=50)
        table.add_column("Status", style="green", overflow="fold")

        if not tool_calls_list_of_dicts:
            return tool_results_for_history

        for tool_call_dict in tool_calls_list_of_dicts:
            function_details = tool_call_dict.get("function", {})
            function_name = function_details.get("name")
            args_str = function_details.get("arguments") # This is a string
            tool_call_id = tool_call_dict.get("id")

            status_display = "[red]Error[/red]" # Default status
            tool_output_content_str = "" # For history

            if function_name in self.available_functions:
                function_to_call = self.available_functions[function_name]
                if args_str is not None and tool_call_id is not None:
                    try:
                        function_args = json.loads(args_str)
                        # Pass necessary dependencies to the tool function
                        function_response_obj = function_to_call(
                            session=self.session,
                            client=self.client,
                            config=app_config, # Pass the whole config module
                            **function_args # The specific arguments for the tool
                        )
                        
                        if isinstance(function_response_obj, dict):
                            tool_output_content_str = json.dumps(function_response_obj)
                            status_display = f"[green]{function_response_obj.get('status', 'unknown').capitalize()}[/green]"
                            # Display tool result (optional, can be verbose)
                            console.print(Panel(Syntax(json.dumps(function_response_obj, indent=2), "json", theme="default", word_wrap=True), title=f"Result: [cyan]{function_name}[/]", border_style="green", expand=False))
                        else: # Should ideally always be a dict for consistency
                            tool_output_content_str = str(function_response_obj) # Fallback
                            status_display = "[yellow]Non-dict result[/yellow]"
                            console.print(f"[yellow]Warning:[/yellow] Tool {function_name} returned a non-dictionary type: {tool_output_content_str}")

                    except json.JSONDecodeError as e:
                        err_msg = f"Invalid JSON arguments for tool '{function_name}': {str(e)}. Args received: {args_str}"
                        tool_output_content_str = json.dumps({"error": err_msg})
                        console.print(Panel(f"Invalid JSON arguments for {function_name}: {args_str}\nError: {e}", title="[bold red]Tool Argument Error[/]", border_style="red"))
                    except TypeError as e: # Mismatched arguments for the tool function
                        err_msg = f"Incorrect arguments when calling tool '{function_name}': {str(e)}. Args received: {args_str}"
                        tool_output_content_str = json.dumps({"error": err_msg})
                        console.print(Panel(f"Argument error for tool {function_name} with args {args_str}:\nError: {e}", title="[bold red]Tool Call Error[/]", border_style="red"))
                    except Exception as e: # Catch-all for other errors during tool execution
                        err_msg = f"Exception during execution of tool '{function_name}': {type(e).__name__} - {str(e)}. Args received: {args_str}"
                        tool_output_content_str = json.dumps({"error": err_msg})
                        console.print(Panel(f"Error executing tool {function_name}:\n{type(e).__name__}: {e}", title="[bold red]Tool Execution Error[/]", border_style="red"))
                else: # Missing args_str or tool_call_id
                    err_msg = f"Malformed tool_call object for function '{function_name}'. Missing arguments string or tool_call_id."
                    tool_output_content_str = json.dumps({"error": err_msg})
                    console.print(Panel(f"Malformed tool_call for '{function_name}': {tool_call_dict}", title="[bold red]Malformed Tool Call[/]", border_style="red"))
            else: # Function name not found in available_functions
                err_msg = f"Function '{function_name}' not found or not implemented by the agent."
                tool_output_content_str = json.dumps({"error": err_msg})
                console.print(Panel(f"LLM requested an unknown function: '{function_name}'", title="[bold red]Unknown Tool Function[/]", border_style="red"))
                status_display = "[red]Unknown Function[/red]"
            
            table.add_row(str(tool_call_id), str(function_name), str(args_str), status_display)
            tool_results_for_history.append({
                "tool_call_id": str(tool_call_id), # Must be a string
                "role": "tool",
                "name": str(function_name), # Must be a string
                "content": tool_output_content_str # Must be a string (JSON string of results)
            })
        
        console.print(table)
        return tool_results_for_history

    def process_input(self, user_input):
        # Ensure system instructions are always first in message history
        if not self.message_history or self.message_history[0].get("role") != "system":
            self.message_history.insert(0, {"role": "system", "content": self.system_instructions})
        self.message_history.append({"role": "user", "content": user_input})
        
        # For simplicity, using a fixed model. Could be made configurable.
        model = "openai-large" 
        
        console.rule("[bold blue]Processing Request[/]")
        # Send a copy of the history to avoid modification by _chat_completion_with_tools if it were to do so
        # (though current implementation appends to self.message_history directly)
        messages_to_send = list(self.message_history) 
        
        assistant_response_dict = self._chat_completion_with_tools(messages_to_send, model=model)
        
        if assistant_response_dict:
            # The final content from the assistant (could be None if last action was a tool_call without a followup text response)
            return assistant_response_dict.get("content", "[Agent Info: No textual content in final assistant message. Tool actions may have occurred.]")
        else:
            return "[Agent Info: Failed to get a response from the assistant after processing.]"

    def get_session(self):
        """Allows external components to access the agent's session."""
        return self.session
