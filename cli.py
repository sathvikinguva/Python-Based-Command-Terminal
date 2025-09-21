"""
Main CLI interface for PyTerm.
Provides the REPL loop with history, autocomplete, and command execution.
"""

import os
import sys
import shlex
from pathlib import Path
import logging
from typing import Dict, Optional

# Rich imports for beautiful output
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.traceback import install

# Prompt toolkit imports for interactive CLI
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.shortcuts import CompleteStyle
    from prompt_toolkit.styles import Style
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

# Local imports
from executor import SafeExecutor, Config
from commands import (
    PWDCommand, LSCommand, CDCommand, MkdirCommand, RMCommand, 
    HelpCommand, ExitCommand
)
from monitor import MonitorCommand
from nl_parser import AICommand, AskCommand, DoCommand

if PROMPT_TOOLKIT_AVAILABLE:
    from autocomplete import PyTermCompleter


class PyTerminal:
    """Main terminal application class."""
    
    def __init__(self, config_path: str = "config.yml"):
        # Install rich traceback handler for better error display
        install(show_locals=True)
        
        # Initialize configuration and executor
        self.config = Config(config_path)
        self.executor = SafeExecutor(self.config)
        self.console = Console()
        
        # Initialize command registry
        self.commands: Dict[str, any] = {}
        self._register_commands()
        
        # Initialize prompt session if available
        self.session: Optional[PromptSession] = None
        self._init_prompt_session()
        
        # Terminal state
        self.running = True
        
        # Show welcome message
        self._show_welcome()
    
    def _register_commands(self):
        """Register all available commands."""
        # Core commands
        self.commands['pwd'] = PWDCommand(self.executor)
        self.commands['ls'] = LSCommand(self.executor)
        self.commands['cd'] = CDCommand(self.executor)
        self.commands['mkdir'] = MkdirCommand(self.executor)
        self.commands['rm'] = RMCommand(self.executor)
        self.commands['exit'] = ExitCommand(self.executor)
        self.commands['quit'] = ExitCommand(self.executor)  # Alias
        
        # Help command (needs access to command registry)
        self.commands['help'] = HelpCommand(self.executor, self.commands)
        
        # Monitor command
        self.commands['monitor'] = MonitorCommand(self.executor)
        
        # AI commands (if enabled)
        if self.config.get('ai_enabled', False):
            self.commands['ai'] = AICommand(self.executor, self.commands)
            self.commands['ask'] = AskCommand(self.executor, self.commands)
            self.commands['do'] = DoCommand(self.executor, self.commands)
        
        # Command aliases
        self.commands['ll'] = LSCommand(self.executor)  # Long listing
        self.commands['la'] = LSCommand(self.executor)  # All files
    
    def _init_prompt_session(self):
        """Initialize prompt_toolkit session if available."""
        if not PROMPT_TOOLKIT_AVAILABLE:
            self.console.print("[yellow]Warning: prompt_toolkit not available. Using basic input.[/yellow]")
            return
        
        try:
            # History file
            history_file = self.config.get('history_file', '.pyterm_history')
            history = FileHistory(history_file)
            
            # Completer
            completer = PyTermCompleter(self.commands, self.executor)
            
            # Style
            style = Style.from_dict({
                'prompt': 'cyan bold',
                'path': 'blue',
                'error': 'red',
                'success': 'green',
            }) if self.config.get('colors_enabled', True) else None
            
            # Create session
            self.session = PromptSession(
                history=history,
                completer=completer,
                complete_style=CompleteStyle.READLINE_LIKE,
                style=style,
                mouse_support=True,
                enable_history_search=True,
            )
            
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not initialize advanced prompt: {e}[/yellow]")
            self.session = None
    
    def _show_welcome(self):
        """Show welcome message."""
        welcome_text = Text()
        welcome_text.append("PyTerm", style="bold cyan")
        welcome_text.append(" - Python-Powered Terminal\n", style="cyan")
        welcome_text.append("Type ", style="dim")
        welcome_text.append("help", style="bold")
        welcome_text.append(" for available commands or ", style="dim")
        welcome_text.append("exit", style="bold")
        welcome_text.append(" to quit.", style="dim")
        
        if self.config.get('ai_enabled', False):
            welcome_text.append("\\n\\nAI features enabled! Use ", style="dim")
            welcome_text.append("ask", style="bold green")
            welcome_text.append(" or ", style="dim")
            welcome_text.append("do", style="bold green")
            welcome_text.append(" followed by natural language.", style="dim")
        
        panel = Panel(
            welcome_text,
            title="Welcome",
            border_style="cyan",
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    def _get_prompt(self) -> str:
        """Generate the command prompt."""
        cwd = Path.cwd()
        
        # Try to make path relative to home
        try:
            home = Path.home()
            if cwd.is_relative_to(home):
                rel_path = '~' / cwd.relative_to(home)
                path_str = str(rel_path).replace('\\\\', '/')
            else:
                path_str = str(cwd).replace('\\\\', '/')
        except (ValueError, OSError):
            path_str = str(cwd).replace('\\\\', '/')
        
        # Truncate long paths
        if len(path_str) > 40:
            path_str = '...' + path_str[-37:]
        
        if self.config.get('colors_enabled', True) and PROMPT_TOOLKIT_AVAILABLE:
            return f"[blue]{path_str}[/blue] {self.config.get('prompt', '> ')}"
        else:
            return f"{path_str} {self.config.get('prompt', '> ')}"
    
    def _get_input(self, prompt: str) -> Optional[str]:
        """Get input from user with appropriate method."""
        try:
            if self.session:
                # Use prompt_toolkit for rich input
                from prompt_toolkit.formatted_text import HTML
                prompt_html = HTML(prompt.replace('[blue]', '<blue>').replace('[/blue]', '</blue>'))
                return self.session.prompt(prompt_html)
            else:
                # Fallback to basic input
                return input(prompt.replace('[blue]', '').replace('[/blue]', ''))
        except (EOFError, KeyboardInterrupt):
            return None
    
    def run(self):
        """Main REPL loop."""
        try:
            while self.running:
                try:
                    # Get input
                    prompt = self._get_prompt()
                    user_input = self._get_input(prompt)
                    
                    if user_input is None:
                        # EOF or Ctrl+C
                        break
                    
                    user_input = user_input.strip()
                    if not user_input:
                        continue
                    
                    # Parse command
                    try:
                        parts = shlex.split(user_input)
                    except ValueError as e:
                        self.console.print(f"[red]Parse error: {e}[/red]")
                        continue
                    
                    if not parts:
                        continue
                    
                    command_name = parts[0]
                    args = parts[1:]
                    
                    # Handle special cases for aliases
                    if command_name == 'll':
                        args = ['-l'] + args
                        command_name = 'ls'
                    elif command_name == 'la':
                        args = ['-a'] + args
                        command_name = 'ls'
                    
                    # Execute command
                    success = self._execute_command(command_name, args)
                    
                    # Handle exit command - exit commands return False to signal exit
                    if command_name in ['exit', 'quit']:
                        break
                    
                except KeyboardInterrupt:
                    self.console.print("\\n[yellow]Use 'exit' to quit[/yellow]")
                    continue
                except Exception as e:
                    self.console.print(f"[red]Unexpected error: {e}[/red]")
                    if self.config.get('log_level') == 'DEBUG':
                        import traceback
                        traceback.print_exc()
        
        except Exception as e:
            self.console.print(f"[red]Fatal error: {e}[/red]")
            return 1
        
        finally:
            self._cleanup()
        
        return 0
    
    def _execute_command(self, command_name: str, args: list) -> bool:
        """Execute a command with given arguments."""
        if command_name not in self.commands:
            self.console.print(f"[red]Unknown command: {command_name}[/red]")
            self.console.print("Type [bold]help[/bold] for available commands.")
            return False
        
        try:
            # Validate arguments
            if not self.executor.validate_command_args(args):
                self.console.print("[red]Invalid or potentially dangerous arguments[/red]")
                return False
            
            # Execute command
            command = self.commands[command_name]
            return command.execute(args)
            
        except Exception as e:
            self.console.print(f"[red]Error executing {command_name}: {e}[/red]")
            if self.config.get('log_level') == 'DEBUG':
                import traceback
                traceback.print_exc()
            return False
    
    def _cleanup(self):
        """Clean up resources before exit."""
        self.console.print("\\n[dim]Goodbye![/dim]")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PyTerm - Python-powered terminal")
    parser.add_argument('--config', '-c', default='config.yml', 
                       help='Configuration file path')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug logging')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Enable dry-run mode (no actual changes)')
    
    args = parser.parse_args()
    
    # Set up logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        # Create terminal instance
        terminal = PyTerminal(args.config)
        
        # Override config with command line args
        if args.dry_run:
            terminal.executor.dry_run = True
            terminal.console.print("[yellow]Dry-run mode enabled - no changes will be made[/yellow]")
        
        # Run the terminal
        return terminal.run()
        
    except KeyboardInterrupt:
        print("\\nInterrupted")
        return 1
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())