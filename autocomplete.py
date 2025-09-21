"""
Autocomplete functionality for PyTerm.
Provides intelligent completion for commands, paths, and flags.
"""

from pathlib import Path
from typing import Iterable
from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter
from prompt_toolkit.document import Document

from executor import SafeExecutor


class PyTermCompleter(Completer):
    """Smart completer for PyTerm commands and arguments."""
    
    def __init__(self, command_registry: dict, executor: SafeExecutor):
        self.command_registry = command_registry
        self.executor = executor
        
        # Initialize sub-completers
        self.command_completer = WordCompleter(
            list(command_registry.keys()), 
            ignore_case=True,
            meta_dict={name: cmd.help().split(' - ', 1)[1] if ' - ' in cmd.help() else cmd.help()
                      for name, cmd in command_registry.items()}
        )
        self.path_completer = SafePathCompleter(executor)
        
        # Common flags for commands
        self.common_flags = {
            'ls': ['-a', '--all', '-l', '--long'],
            'rm': ['-r', '--recursive', '-f', '--force', '-v', '--verbose'],
            'mkdir': ['-p', '--parents', '-v', '--verbose'],
        }
    
    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Get completions for the current input."""
        text = document.text_before_cursor
        words = text.split()
        
        if not text or not words:
            # Complete command names at the start
            yield from self.command_completer.get_completions(document, complete_event)
            return
        
        if len(words) == 1 and not text.endswith(' '):
            # Still completing the command name
            yield from self.command_completer.get_completions(document, complete_event)
            return
        
        # Get the command name
        command = words[0]
        
        if command not in self.command_registry:
            return
        
        # Get current word being completed
        if text.endswith(' '):
            current_word = ''
            word_start = len(text)
        else:
            current_word = words[-1]
            word_start = len(text) - len(current_word)
        
        # Complete flags
        if current_word.startswith('-'):
            flags = self.common_flags.get(command, [])
            for flag in flags:
                if flag.startswith(current_word):
                    yield Completion(
                        flag,
                        start_position=-len(current_word),
                        display=flag,
                        meta=self._get_flag_description(command, flag)
                    )
            return
        
        # Complete paths for most commands
        if command in ['ls', 'cd', 'rm', 'mkdir']:
            # Create a modified document for path completion
            path_doc = Document(
                text=current_word,
                cursor_position=len(current_word)
            )
            
            for completion in self.path_completer.get_completions(path_doc, complete_event):
                yield Completion(
                    completion.text,
                    start_position=-len(current_word),
                    display=completion.display or completion.text,
                    meta=completion.meta
                )
    
    def _get_flag_description(self, command: str, flag: str) -> str:
        """Get description for a command flag."""
        descriptions = {
            'ls': {
                '-a': 'Show all files including hidden',
                '--all': 'Show all files including hidden',
                '-l': 'Use long listing format',
                '--long': 'Use long listing format'
            },
            'rm': {
                '-r': 'Remove directories recursively',
                '--recursive': 'Remove directories recursively',
                '-f': 'Force removal without confirmation',
                '--force': 'Force removal without confirmation',
                '-v': 'Verbose output',
                '--verbose': 'Verbose output'
            },
            'mkdir': {
                '-p': 'Create parent directories as needed',
                '--parents': 'Create parent directories as needed',
                '-v': 'Verbose output',
                '--verbose': 'Verbose output'
            }
        }
        
        return descriptions.get(command, {}).get(flag, '')


class SafePathCompleter(Completer):
    """Path completer that respects security restrictions."""
    
    def __init__(self, executor: SafeExecutor):
        self.executor = executor
        self.base_completer = PathCompleter(only_directories=False)
    
    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Get path completions that are safe to access."""
        text = document.text_before_cursor
        
        # Let the base completer do most of the work
        for completion in self.base_completer.get_completions(document, complete_event):
            try:
                # Check if the completion would result in a safe path
                completed_path = text[:document.cursor_position + completion.start_position] + completion.text
                
                # Try to resolve the path safely
                self.executor.safe_resolve(completed_path)
                
                # Add metadata for directories
                full_path = Path(completed_path)
                if full_path.is_dir():
                    completion.meta = "directory"
                elif full_path.is_file():
                    completion.meta = f"file ({self._get_file_type(full_path)})"
                
                yield completion
                
            except Exception:
                # Skip unsafe completions
                continue
    
    def _get_file_type(self, path: Path) -> str:
        """Get a description of the file type."""
        if not path.exists():
            return "unknown"
        
        suffix = path.suffix.lower()
        type_map = {
            '.py': 'Python',
            '.txt': 'text',
            '.md': 'Markdown',
            '.yml': 'YAML',
            '.yaml': 'YAML',
            '.json': 'JSON',
            '.csv': 'CSV',
            '.log': 'log file',
            '.exe': 'executable',
            '.bat': 'batch file',
            '.ps1': 'PowerShell',
            '.sh': 'shell script'
        }
        
        return type_map.get(suffix, 'file')


class HistoryCompleter(Completer):
    """Completer that suggests from command history."""
    
    def __init__(self, history_file: str = ".pyterm_history"):
        self.history_file = history_file
        self.cached_commands = []
        self._load_history()
    
    def _load_history(self):
        """Load recent commands from history file."""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-100:]  # Last 100 commands
                self.cached_commands = [line.strip() for line in lines if line.strip()]
        except FileNotFoundError:
            self.cached_commands = []
    
    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Get completions from history."""
        text = document.text_before_cursor.lower()
        
        if not text:
            return
        
        seen = set()
        for cmd in reversed(self.cached_commands):
            if cmd.lower().startswith(text) and cmd not in seen:
                seen.add(cmd)
                yield Completion(
                    cmd,
                    start_position=-len(text),
                    meta="from history"
                )