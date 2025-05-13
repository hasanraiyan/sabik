# sabik_agent/interface.py
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

# Global console instance for consistent Rich output
console = Console()

# You could add CLI-specific helper functions here if needed later