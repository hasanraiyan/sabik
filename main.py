# main.py - Entry point for the Sabik AI Agent CLI

import os
import sys

# Ensure the sabik_agent package can be found if running main.py directly from sabik/
# This is useful for development. For installation, setup.py would handle paths.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir # In this case, sabik/ is the project root
sys.path.insert(0, project_root)


from sabik_agent.agent import AdvancedSabikAgent
from sabik_agent.interface import console, Panel
from sabik_agent import config as app_config # For OUTPUT_DIR or other direct config needs

def run_cli():
    # Output directory is created by config.py when imported
    # os.makedirs(app_config.OUTPUT_DIR, exist_ok=True) # Redundant if config.py does it

    agent = AdvancedSabikAgent()
    
    console.print(Panel(f"""[bold]Sabik AI Agent[/]
Referrer: [cyan]{agent.referrer}[/cyan]
LLM API: [cyan]{app_config.OPENAI_BASE_URL_TEXT}[/cyan]
Image API: [cyan]{app_config.OPENAI_IMAGE_BASE_URL_TEXT}[/cyan]
Output Dir: [cyan]{app_config.OUTPUT_DIR}[/cyan]

The agent uses Large Language Models with tool-calling capabilities.
Responses are not streamed in this version for simplicity with tool integration.
""", title="[bold green]Welcome to Sabik AI![/]", border_style="green", expand=False))

    console.print(Panel("""[bold]Available Commands & Usage Examples:[/bold]
  - Simply type your request for the agent, e.g.:
    - "Generate an image of a futuristic city at sunset."
    - "What is depicted in the image located at ./my_photo.jpg? Is there a cat?"
    - "Transcribe the audio content from the file meeting_recording.wav."
    - "Can you say 'Hello, world!' using the 'echo' voice?"
    - "What is the result of (350 / 7) * 3 + 15?"
    - "Fetch the main content from the webpage https://example.com"
  - To exit:
    - [cyan]quit[/cyan] or [cyan]exit[/cyan]
""", title="Help & Instructions", border_style="blue", expand=False))

    try:
        while True:
            try:
                user_input = console.input("[bold chart_reuse]You> [/bold chart_reuse]")
            except EOFError:
                console.print("\n[yellow]EOF received. Exiting Sabik AI...[/yellow]")
                break
            except KeyboardInterrupt:
                console.print("\n[yellow]Keyboard interrupt detected. Exiting Sabik AI...[/yellow]")
                break

            command = user_input.lower().strip()

            if command in ["quit", "exit"]:
                console.print("[yellow]Exiting Sabik AI...[/yellow]")
                break
            
            if not command: # Empty input
                continue

            # Process the input with the agent
            final_response_content = agent.process_input(user_input)
            
            # The agent's _chat_completion_with_tools already prints the final assistant response panel.
            # If final_response_content contains specific info messages, we can print them here.
            if final_response_content and isinstance(final_response_content, str) and final_response_content.startswith("[Agent Info:"):
                 console.print(f"[italic yellow]{final_response_content}[/italic yellow]")
            
            console.rule(style="dim grey50") # Separator after processing each command

    finally:
        console.print("[bold green]Sabik AI shut down gracefully.[/bold green]")

if __name__ == "__main__":
    run_cli()
