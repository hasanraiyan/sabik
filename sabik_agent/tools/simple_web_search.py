import requests
from ..interface import console, Panel

def simple_web_search(url, *, session, client, config, **kwargs):
    console.print(Panel(f"Tool: Simple Web Search\nURL: [link={url}]{url}[/link]", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    try:
        if not url.startswith(('http://', 'https://')):
            return {"status": "error", "message": "Invalid URL. Must start with http:// or https://"}
        console.print(f"[grey50 i]Fetching {url}...[/grey50 i]")
        response = session.get(url, timeout=10)
        response.raise_for_status()
        content_summary = f"Successfully fetched content from {url}. Content length: {len(response.text)}. (Full content parsing not implemented in this simple tool)."
        return {"status": "success", "url": url, "summary": content_summary, "message": f"Fetched content from {url}."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "url": url, "message": f"Failed to fetch URL {url}: {str(e)}"}
    except Exception as e:
        return {"status": "error", "url": url, "message": f"An unexpected error occurred during web search for {url}: {str(e)}"}
