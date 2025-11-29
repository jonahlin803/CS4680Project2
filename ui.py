"""User Interface module for the AI Agent."""
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.syntax import Syntax
from typing import Optional
from logger import logger


class UserInterface:
    """Terminal-based user interface for the AI Agent."""
    
    def __init__(self):
        """Initialize the UI."""
        self.console = Console()
        self.show_welcome()
    
    def show_welcome(self):
        """Display welcome message."""
        welcome_text = """
# AI Agent

An intelligent agent that interprets LLM responses and executes actions.

Type your requests in natural language, and the agent will:
- Understand your intent
- Plan the necessary actions
- Execute them safely
- Provide feedback on results

Type 'help' for commands, 'exit' to quit.
"""
        self.console.print(Panel(Markdown(welcome_text), title="Welcome", border_style="blue"))
    
    def get_user_input(self) -> Optional[str]:
        """
        Get input from the user.
        
        Returns:
            User input string or None if user wants to exit
        """
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                return None
            
            if user_input.lower() == 'help':
                self.show_help()
                return self.get_user_input()
            
            return user_input
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted by user[/yellow]")
            return None
        except EOFError:
            return None
    
    def show_help(self):
        """Display help information."""
        help_text = """
## Available Commands

- **help** - Show this help message
- **exit/quit/q** - Exit the agent

## Example Requests

- "Create a file called test.txt with the content 'Hello World'"
- "List all files in the current directory"
- "Read the contents of README.md"
- "What is the weather like today?"
- "Execute the command 'python --version'"

## Safety Features

The agent will ask for confirmation before:
- Deleting files
- Running potentially dangerous system commands
- Making destructive API calls
- Performing database operations that modify data
"""
        self.console.print(Panel(Markdown(help_text), title="Help", border_style="green"))
    
    def show_llm_thinking(self, message: str = "Thinking..."):
        """Show that the LLM is processing."""
        self.console.print(f"[yellow]🤔 {message}[/yellow]")
    
    def show_action(self, action_type: str, explanation: str):
        """Display the action being taken."""
        self.console.print(f"[blue]📋 Action:[/blue] {action_type}")
        if explanation:
            self.console.print(f"[dim]{explanation}[/dim]")
    
    def show_result(self, success: bool, message: str):
        """Display the result of an action."""
        if success:
            self.console.print(Panel(
                message,
                title="[green]✓ Success[/green]",
                border_style="green"
            ))
        else:
            self.console.print(Panel(
                message,
                title="[red]✗ Error[/red]",
                border_style="red"
            ))
    
    def show_information(self, message: str):
        """Display information from the LLM."""
        self.console.print(Panel(
            Markdown(message),
            title="[cyan]ℹ Information[/cyan]",
            border_style="cyan"
        ))
    
    def request_confirmation(self, action_type: str, action_details: dict) -> bool:
        """
        Request user confirmation for a potentially dangerous action.
        
        Returns:
            True if user confirms, False otherwise
        """
        self.console.print("\n[bold red]⚠ Warning: This action may be destructive![/bold red]")
        self.console.print(f"[yellow]Action Type:[/yellow] {action_type}")
        self.console.print(f"[yellow]Details:[/yellow] {action_details}")
        
        return Confirm.ask("\n[bold]Do you want to proceed?[/bold]", default=False)
    
    def show_error(self, error: str):
        """Display an error message."""
        self.console.print(f"[red]Error: {error}[/red]")
    
    def show_goodbye(self):
        """Display goodbye message."""
        self.console.print("\n[yellow]Goodbye! Thanks for using AI Agent.[/yellow]")

