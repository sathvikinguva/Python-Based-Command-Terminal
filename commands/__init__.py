"""
Core command implementations for PyTerm.
All basic shell-like commands with safety checks.
"""

import os
import stat
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.text import Text

from executor import SafeExecutor, SecurityError


class Command:
    """Base class for all commands."""
    
    def __init__(self, executor: SafeExecutor):
        self.executor = executor
        self.console = Console()
    
    def execute(self, args: List[str]) -> bool:
        """Execute the command with given arguments."""
        raise NotImplementedError
    
    def help(self) -> str:
        """Return help text for the command."""
        raise NotImplementedError


class PWDCommand(Command):
    """Print working directory command."""
    
    def execute(self, args: List[str]) -> bool:
        try:
            current_dir = Path.cwd()
            self.console.print(str(current_dir))
            return True
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            return False
    
    def help(self) -> str:
        return "pwd - Print the current working directory"


class LSCommand(Command):
    """List directory contents command."""
    
    def execute(self, args: List[str]) -> bool:
        # Parse flags
        show_all = '-a' in args or '--all' in args
        long_format = '-l' in args or '--long' in args
        
        # Remove flags from args to get target path
        target_args = [arg for arg in args if not arg.startswith('-')]
        target = target_args[0] if target_args else "."
        
        try:
            path = self.executor.safe_resolve(target)
            
            if not self.executor.check_permissions(path, 'read'):
                self.console.print(f"[red]Permission denied: {path}[/red]")
                return False
            
            if path.is_file():
                self._show_file_info(path, long_format)
                return True
            
            if not path.is_dir():
                self.console.print(f"[red]Not a directory: {path}[/red]")
                return False
            
            # List directory contents
            entries = []
            try:
                for entry in path.iterdir():
                    if not show_all and entry.name.startswith('.'):
                        continue
                    entries.append(entry)
            except PermissionError:
                self.console.print(f"[red]Permission denied reading directory: {path}[/red]")
                return False
            
            # Sort entries
            entries.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            if long_format:
                self._show_long_format(entries)
            else:
                self._show_simple_format(entries)
            
            return True
            
        except SecurityError as e:
            self.console.print(f"[red]{e}[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            return False
    
    def _show_file_info(self, path: Path, long_format: bool):
        """Show information for a single file."""
        if long_format:
            self._show_long_format([path])
        else:
            name = path.name
            if path.is_dir():
                name = f"[blue]{name}/[/blue]"
            elif path.is_symlink():
                name = f"[cyan]{name}[/cyan]"
            self.console.print(name)
    
    def _show_simple_format(self, entries: List[Path]):
        """Show entries in simple format."""
        for entry in entries:
            name = entry.name
            if entry.is_dir():
                name = f"[blue]{name}/[/blue]"
            elif entry.is_symlink():
                name = f"[cyan]{name}[/cyan]"
            elif entry.suffix in ['.py', '.exe', '.bat', '.sh']:
                name = f"[green]{name}[/green]"
            
            self.console.print(name)
    
    def _show_long_format(self, entries: List[Path]):
        """Show entries in long format with details."""
        table = Table(show_header=False, padding=(0, 2))
        table.add_column("Permissions", style="dim")
        table.add_column("Size", justify="right", style="dim")
        table.add_column("Modified", style="dim")
        table.add_column("Name")
        
        for entry in entries:
            try:
                stat_info = entry.stat()
                
                # Permissions
                mode = stat.filemode(stat_info.st_mode)
                
                # Size
                if entry.is_dir():
                    size = "-"
                else:
                    size = self._format_size(stat_info.st_size)
                
                # Modified time
                mod_time = datetime.fromtimestamp(stat_info.st_mtime)
                mod_str = mod_time.strftime("%b %d %H:%M")
                
                # Name with colors
                name = entry.name
                if entry.is_dir():
                    name = f"[blue]{name}/[/blue]"
                elif entry.is_symlink():
                    name = f"[cyan]{name}[/cyan]"
                elif entry.suffix in ['.py', '.exe', '.bat', '.sh']:
                    name = f"[green]{name}[/green]"
                
                table.add_row(mode, size, mod_str, name)
                
            except (OSError, PermissionError):
                table.add_row("?", "?", "?", f"[red]{entry.name}[/red]")
        
        self.console.print(table)
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'K', 'M', 'G', 'T']:
            if size < 1024:
                return f"{size:.1f}{unit}" if size != int(size) else f"{int(size)}{unit}"
            size /= 1024
        return f"{size:.1f}P"
    
    def help(self) -> str:
        return "ls [-a|--all] [-l|--long] [path] - List directory contents"


class CDCommand(Command):
    """Change directory command."""
    
    def execute(self, args: List[str]) -> bool:
        if not args:
            # Go to home directory
            target = Path.home()
        else:
            target = args[0]
        
        try:
            path = self.executor.safe_resolve(str(target))
            
            if not path.exists():
                self.console.print(f"[red]Directory not found: {target}[/red]")
                return False
            
            if not path.is_dir():
                self.console.print(f"[red]Not a directory: {target}[/red]")
                return False
            
            if not self.executor.check_permissions(path, 'read'):
                self.console.print(f"[red]Permission denied: {path}[/red]")
                return False
            
            os.chdir(path)
            return True
            
        except SecurityError as e:
            self.console.print(f"[red]{e}[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            return False
    
    def help(self) -> str:
        return "cd [directory] - Change current directory"


class MkdirCommand(Command):
    """Make directory command."""
    
    def execute(self, args: List[str]) -> bool:
        if not args:
            self.console.print("[red]mkdir: missing operand[/red]")
            return False
        
        # Parse flags
        parents = '-p' in args or '--parents' in args
        verbose = '-v' in args or '--verbose' in args
        
        # Remove flags from args to get directory names
        dir_args = [arg for arg in args if not arg.startswith('-')]
        
        if not dir_args:
            self.console.print("[red]mkdir: missing directory operand[/red]")
            return False
        
        success = True
        for dir_name in dir_args:
            try:
                path = self.executor.safe_resolve(dir_name)
                
                if path.exists():
                    self.console.print(f"[yellow]Directory already exists: {dir_name}[/yellow]")
                    continue
                
                if not self.executor.check_permissions(path.parent, 'write'):
                    self.console.print(f"[red]Permission denied: {path.parent}[/red]")
                    success = False
                    continue
                
                if self.executor.dry_run:
                    self.console.print(f"[dim]DRY RUN: Would create directory {path}[/dim]")
                    continue
                
                path.mkdir(parents=parents, exist_ok=False)
                
                if verbose:
                    self.console.print(f"Created directory: {path}")
                
            except FileExistsError:
                self.console.print(f"[yellow]Directory already exists: {dir_name}[/yellow]")
            except SecurityError as e:
                self.console.print(f"[red]{e}[/red]")
                success = False
            except Exception as e:
                self.console.print(f"[red]Error creating {dir_name}: {e}[/red]")
                success = False
        
        return success
    
    def help(self) -> str:
        return "mkdir [-p|--parents] [-v|--verbose] directory... - Create directories"


class RMCommand(Command):
    """Remove files and directories command."""
    
    def execute(self, args: List[str]) -> bool:
        if not args:
            self.console.print("[red]rm: missing operand[/red]")
            return False
        
        # Parse flags
        recursive = '-r' in args or '--recursive' in args or '-rf' in args
        force = '-f' in args or '--force' in args or '-rf' in args
        verbose = '-v' in args or '--verbose' in args
        
        # Remove flags from args to get file names
        file_args = [arg for arg in args if not arg.startswith('-')]
        
        if not file_args:
            self.console.print("[red]rm: missing file operand[/red]")
            return False
        
        success = True
        for file_name in file_args:
            try:
                path = self.executor.safe_resolve(file_name)
                
                if not path.exists():
                    if not force:
                        self.console.print(f"[red]File not found: {file_name}[/red]")
                        success = False
                    continue
                
                if path.is_dir() and not recursive:
                    self.console.print(f"[red]Is a directory (use -r for recursive): {file_name}[/red]")
                    success = False
                    continue
                
                if not self.executor.check_permissions(path, 'delete'):
                    self.console.print(f"[red]Permission denied: {file_name}[/red]")
                    success = False
                    continue
                
                # Confirm for recursive deletion
                if path.is_dir() and recursive and not force:
                    response = input(f"Remove directory '{path}' and all its contents? (y/N): ")
                    if response.lower() not in ['y', 'yes']:
                        self.console.print("Cancelled")
                        continue
                
                if self.executor.safe_delete(path):
                    if verbose:
                        self.console.print(f"Removed: {path}")
                else:
                    success = False
                
            except SecurityError as e:
                self.console.print(f"[red]{e}[/red]")
                success = False
            except Exception as e:
                self.console.print(f"[red]Error removing {file_name}: {e}[/red]")
                success = False
        
        return success
    
    def help(self) -> str:
        return "rm [-r|--recursive] [-f|--force] [-v|--verbose] file... - Remove files and directories"


class HelpCommand(Command):
    """Help command."""
    
    def __init__(self, executor: SafeExecutor, command_registry: dict):
        super().__init__(executor)
        self.command_registry = command_registry
    
    def execute(self, args: List[str]) -> bool:
        if args:
            # Help for specific command
            cmd_name = args[0]
            if cmd_name in self.command_registry:
                self.console.print(self.command_registry[cmd_name].help())
            else:
                self.console.print(f"[red]Unknown command: {cmd_name}[/red]")
                return False
        else:
            # General help
            self.console.print("[bold]Available commands:[/bold]")
            table = Table(show_header=False, padding=(0, 2))
            table.add_column("Command", style="cyan")
            table.add_column("Description")
            
            for name, cmd in sorted(self.command_registry.items()):
                help_text = cmd.help().split(' - ', 1)
                desc = help_text[1] if len(help_text) > 1 else help_text[0]
                table.add_row(name, desc)
            
            self.console.print(table)
            self.console.print("\nUse 'help <command>' for detailed help on a specific command.")
        
        return True
    
    def help(self) -> str:
        return "help [command] - Show help for commands"


class ExitCommand(Command):
    """Exit command."""
    
    def execute(self, args: List[str]) -> bool:
        self.console.print("Goodbye!")
        return False  # Signal to exit
    
    def help(self) -> str:
        return "exit - Exit the terminal"