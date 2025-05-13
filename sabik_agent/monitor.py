# sabik_agent/monitor.py
import threading
import time
import json
import requests
import urllib.parse
from datetime import datetime

try:
    import sseclient # type: ignore
except ImportError:
    sseclient = None
    print("sseclient-py not installed. Feed monitoring will not work. pip install sseclient-py")


from .interface import console, Panel, Syntax
# config will be passed to the FeedMonitor instance

class FeedMonitor:
    def __init__(self, session, config_module):
        self.session = session # Use the agent's session
        self.config = config_module
        self.feed_threads = {}
        self.stop_event = threading.Event()
        if sseclient is None:
            console.print("[bold red]Warning: sseclient-py is not installed. Feed monitoring functionality will be disabled.[/bold red]")


    def _monitor_feed_worker(self, feed_url, feed_name):
        if sseclient is None:
            console.print(f"[yellow]{feed_name} monitoring disabled as sseclient is not available.[/yellow]")
            return

        console.print(Panel(f"Starting Monitor Thread: {threading.current_thread().name} for {feed_name}", title=f"[bold green]{feed_name} Monitor[/]", border_style="green"))
        while not self.stop_event.is_set():
            try:
                # Use self.session for requests, which should have referrer and other headers
                response = self.session.get(feed_url, stream=True, headers={'Accept': 'text/event-stream'}, timeout=(10, 60)) # connect timeout, read timeout
                response.raise_for_status()
                
                sse_client = sseclient.SSEClient(response)
                console.print(f"[green dim]{feed_name} connected to {feed_url}.[/green dim]")
                
                for event in sse_client.events():
                    if self.stop_event.is_set():
                        break
                    if event.data:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        console.rule(style="dim cyan")
                        try:
                            data_dict = json.loads(event.data)
                            # Pretty print JSON if it's valid
                            syntax_element = Syntax(json.dumps(data_dict, indent=2), "json", theme="default", line_numbers=False, word_wrap=True)
                            console.print(Panel(syntax_element, title=f"[cyan]{feed_name} Event ({timestamp})[/]", border_style="cyan"))
                        except json.JSONDecodeError:
                            # If not JSON, print raw data if it's not just a comment (lines starting with ':')
                            if event.data.strip() and not event.data.startswith(':'):
                                console.print(Panel(event.data, title=f"[yellow]{feed_name} Raw Data ({timestamp})[/]", border_style="yellow"))
                
                if not self.stop_event.is_set(): # If loop finished without stop_event (e.g. stream ended)
                    console.print(f"[yellow dim]{feed_name} stream ended. Retrying in 5 seconds...[/yellow dim]")
                    time.sleep(5)

            except requests.exceptions.Timeout:
                console.print(f"[yellow dim]{feed_name} connection timeout. Retrying in 10 seconds...[/yellow dim]")
                time.sleep(10)
            except requests.exceptions.RequestException as e:
                console.print(f"[yellow dim]{feed_name} connection error: {e}. Retrying in 10 seconds...[/yellow dim]")
                time.sleep(10)
            except Exception as e: # Catch any other unexpected error in the loop
                console.print(f"[red dim]Unexpected error in {feed_name} monitor: {type(e).__name__} - {e}. Retrying in 10s...[/red dim]")
                time.sleep(10)
            
            if self.stop_event.is_set(): # Check again before looping
                break
        
        console.print(Panel(f"Exited Monitor Thread: {threading.current_thread().name}", title=f"[bold red]{feed_name} Monitor Stopped[/]", border_style="red"))

    def start_image_feed_monitor(self):
        if sseclient is None: return False
        feed_key = "image_feed"
        url = f"{self.config.OPENAI_IMAGE_BASE_URL_TEXT}/feed"
        
        if feed_key not in self.feed_threads or not self.feed_threads[feed_key].is_alive():
            self.stop_event.clear() # Ensure stop event is clear if we are restarting
            thread = threading.Thread(target=self._monitor_feed_worker, args=(url, "Image Feed"), daemon=True, name="ImgFeedMonitorThread")
            self.feed_threads[feed_key] = thread
            thread.start()
            console.print("[green]Image feed monitor thread started.[/green]")
            return True
        else:
            console.print("[yellow]Image feed monitor is already running.[/yellow]")
            return False

    def start_text_feed_monitor(self):
        if sseclient is None: return False
        feed_key = "text_feed"
        # Construct base URL for text feed (e.g., https://text.pollinations.ai/feed)
        parsed_url = urllib.parse.urlparse(self.config.OPENAI_BASE_URL_TEXT)
        base_api_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        url = f"{base_api_url}/feed"

        if feed_key not in self.feed_threads or not self.feed_threads[feed_key].is_alive():
            self.stop_event.clear() # Ensure stop event is clear
            thread = threading.Thread(target=self._monitor_feed_worker, args=(url, "Text Feed"), daemon=True, name="TxtFeedMonitorThread")
            self.feed_threads[feed_key] = thread
            thread.start()
            console.print("[green]Text feed monitor thread started.[/green]")
            return True
        else:
            console.print("[yellow]Text feed monitor is already running.[/yellow]")
            return False

    def stop_all_monitors(self):
        if sseclient is None: return
        if not self.feed_threads:
            console.print("[dim]No active monitors to stop.[/dim]")
            return

        console.print("[bold yellow]Stopping all monitor threads...[/]")
        self.stop_event.set() # Signal all monitor threads to stop

        active_threads = []
        for feed_key, thread in self.feed_threads.items():
            if thread.is_alive():
                active_threads.append(thread)
                console.print(f"[dim]Waiting for {thread.name} to stop...[/dim]")
        
        for thread in active_threads:
            thread.join(timeout=5) # Wait for threads to finish
            if thread.is_alive():
                console.print(f"[yellow]Warning: Monitor thread {thread.name} did not stop in time.[/yellow]")

        self.feed_threads = {} # Clear the record of threads
        # self.stop_event.clear() # Clear event for potential future starts - or keep it set until a new start?
                                 # Clearing it here makes sense if stop_all_monitors means a full reset.
                                 # Let's clear it, as start methods also clear it.
        console.print("[bold red]All monitor threads have been signaled to stop.[/bold red]")