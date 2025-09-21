"""
Natural Language Parser for PyTerm using Google AI.
Translates plain English commands to safe shell actions.
"""

import os
import re
import time
from typing import List, Dict, Optional, Tuple
import google.generativeai as genai
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from executor import SafeExecutor
from commands import Command


class AIParser:
    """AI-powered natural language to command parser."""
    
    def __init__(self, executor: SafeExecutor):
        self.executor = executor
        self.console = Console()
        self.last_api_call = 0  # Track last API call for rate limiting
        self.min_api_interval = 2.0  # Minimum seconds between API calls
        
        # Configure Google AI
        api_key = (
            executor.config.get('google_api_key') or 
            os.environ.get('GOOGLE_API_KEY') or
            "AIzaSyDe1RjeTrHHSnkg662Y8F8mS0oVbVUWUU4"  # Your provided key
        )
        
        if api_key:
            genai.configure(api_key=api_key)
            try:
                self.model = genai.GenerativeModel('gemini-pro')
                self.ai_enabled = True
            except Exception as e:
                self.console.print(f"[yellow]Warning: AI initialization failed: {e}[/yellow]")
                self.ai_enabled = False
        else:
            self.ai_enabled = False
    
    def parse_natural_language(self, text: str) -> List[str]:
        """
        Parse natural language text into shell commands.
        
        Args:
            text: Natural language description
            
        Returns:
            List of shell commands to execute
        """
        if not self.ai_enabled:
            return self._fallback_parse(text)
        
        # Rate limiting to prevent quota issues
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        if time_since_last_call < self.min_api_interval:
            wait_time = self.min_api_interval - time_since_last_call
            self.console.print(f"[dim]Rate limiting: waiting {wait_time:.1f}s...[/dim]")
            time.sleep(wait_time)
        
        try:
            prompt = self._build_prompt(text)
            self.last_api_call = time.time()  # Update last call time
            response = self.model.generate_content(prompt)
            
            if response.text:
                return self._extract_commands(response.text)
            else:
                self.console.print("[yellow]AI response was empty, using fallback parser[/yellow]")
                return self._fallback_parse(text)
                
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                self.console.print("[yellow]AI quota exceeded. Using fallback parser.[/yellow]")
                self.console.print("[dim]Tip: Wait a few minutes or use basic commands directly[/dim]")
            elif "403" in error_msg or "api key" in error_msg.lower():
                self.console.print("[yellow]AI API key issue. Using fallback parser.[/yellow]")
                self.console.print("[dim]Check your Google AI API key in config.yml[/dim]")
            else:
                self.console.print(f"[yellow]AI parsing failed: {error_msg}[/yellow]")
                self.console.print("[dim]Using fallback parser instead[/dim]")
            
            return self._fallback_parse(text)
    
    def _build_prompt(self, text: str) -> str:
        """Build the prompt for the AI model."""
        current_dir = os.getcwd()
        
        prompt = f"""You are a command-line assistant that translates natural language into safe shell commands.

Current working directory: {current_dir}
Available commands: ls, cd, pwd, mkdir, rm, help, exit, monitor
Safety rules:
- Only use the available commands listed above
- Never use dangerous commands like format, delete system files, etc.
- Paths should be relative to current directory when possible
- For rm command, always be explicit about what is being deleted
- Use appropriate flags when needed (e.g., -r for recursive, -p for mkdir)

User request: "{text}"

Please translate this into a series of safe shell commands. Return ONLY the commands, one per line, without explanations or additional text. If the request cannot be safely fulfilled, return "UNSAFE_REQUEST".

Examples:
- "list files" → ls
- "create folder test" → mkdir test  
- "go to documents folder" → cd documents
- "remove file.txt" → rm file.txt
- "show system info" → monitor

Commands:"""
        
        return prompt
    
    def _extract_commands(self, response: str) -> List[str]:
        """Extract commands from AI response."""
        lines = response.strip().split('\n')
        commands = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Remove markdown code blocks
            line = re.sub(r'^```.*?$', '', line)
            line = re.sub(r'^`(.*)`$', r'\1', line)
            
            # Skip unsafe requests
            if 'UNSAFE_REQUEST' in line.upper():
                self.console.print("[red]Request deemed unsafe by AI[/red]")
                return []
            
            # Clean up the command
            line = line.strip('`"\'')
            
            if line and self._is_safe_command(line):
                commands.append(line)
        
        return commands
    
    def _is_safe_command(self, command: str) -> bool:
        """Check if a command is safe to execute."""
        safe_commands = ['ls', 'cd', 'pwd', 'mkdir', 'rm', 'help', 'exit', 'monitor']
        
        parts = command.split()
        if not parts:
            return False
        
        cmd_name = parts[0]
        
        # Check if command is in our whitelist
        if cmd_name not in safe_commands:
            return False
        
        # Additional safety checks for rm command
        if cmd_name == 'rm':
            args = parts[1:]
            dangerous_patterns = [
                '*', '/', '\\', '..', '~', 'C:', 'D:', 'system32', 'windows'
            ]
            
            for arg in args:
                arg_lower = arg.lower()
                for pattern in dangerous_patterns:
                    if pattern in arg_lower:
                        return False
        
        return True
    
    def _fallback_parse(self, text: str) -> List[str]:
        """Simple rule-based fallback parser."""
        text_lower = text.lower().strip()
        
        # Simple pattern matching
        patterns = [
            (r'list\s+files?|show\s+files?|^ls$', 'ls'),
            (r'list\s+all|show\s+all|ls\s+all', 'ls -a'),
            (r'list\s+detailed?|ls\s+detailed?', 'ls -l'),
            (r'where\s+am\s+i|current\s+dir|pwd', 'pwd'),
            (r'go\s+to\s+(.+)|change\s+to\s+(.+)|cd\s+(.+)', r'cd \1\2\3'),
            # Enhanced folder creation patterns
            (r'create\s+(?:a\s+)?(?:new\s+)?folder\s+(?:called\s+)?(.+)', r'mkdir \1'),
            (r'make\s+(?:a\s+)?(?:new\s+)?(?:dir|directory)\s+(?:called\s+)?(.+)', r'mkdir \1'),
            (r'create\s+(?:a\s+)?(?:new\s+)?directory\s+(?:called\s+)?(.+)', r'mkdir \1'),
            (r'mkdir\s+(.+)', r'mkdir \1'),
            # File removal patterns  
            (r'delete\s+(.+)|remove\s+(.+)|rm\s+(.+)', r'rm \1\2\3'),
            (r'system\s+info|monitor|show\s+stats', 'monitor'),
            (r'help|show\s+help', 'help'),
            (r'exit|quit', 'exit'),
        ]
        
        for pattern, replacement in patterns:
            match = re.search(pattern, text_lower)
            if match:
                if '\\' in replacement:
                    # Handle capture groups
                    cmd = re.sub(pattern, replacement, text_lower)
                    return [cmd.strip()]
                else:
                    return [replacement]
        
        # No pattern matched
        return []


class AICommand(Command):
    """AI natural language command processor."""
    
    def __init__(self, executor: SafeExecutor, command_registry: dict):
        super().__init__(executor)
        self.command_registry = command_registry
        self.ai_parser = AIParser(executor)
        self.confirmation_required = executor.config.get('ai_confirmation_required', True)
        self.web_mode = False  # Flag to indicate web mode
    
    def set_web_mode(self, web_mode: bool = True):
        """Set web mode to handle confirmations differently."""
        self.web_mode = web_mode
    
    def execute(self, args: List[str]) -> bool:
        """Execute AI command with natural language input."""
        if not args:
            self.console.print("[red]Please provide a natural language command[/red]")
            return False
        
        # Join all arguments to form the natural language query
        query = ' '.join(args)
        
        self.console.print(f"[dim]Processing: {query}[/dim]")
        
        # Parse natural language to commands
        commands = self.ai_parser.parse_natural_language(query)
        
        if not commands:
            self.console.print("[yellow]Could not understand the request or request was unsafe[/yellow]")
            return False
        
        # Display planned commands
        self._show_planned_commands(query, commands)
        
        # Ask for confirmation if required
        if self.confirmation_required:
            if self.web_mode:
                # In web mode, return the planned commands for confirmation
                return {
                    'type': 'confirmation_required',
                    'query': query,
                    'commands': commands,
                    'message': f"Execute these commands?\n{chr(10).join(commands)}"
                }
            else:
                # Terminal mode - ask directly
                if not Confirm.ask("Execute these commands?"):
                    self.console.print("[yellow]Cancelled[/yellow]")
                    return True
        
        # Execute commands
        return self._execute_command_sequence(commands)
    
    def _show_planned_commands(self, query: str, commands: List[str]):
        """Display the planned commands to the user."""
        command_text = '\n'.join(f"  {cmd}" for cmd in commands)
        
        panel = Panel(
            f"[bold]Query:[/bold] {query}\n\n[bold]Planned commands:[/bold]\n{command_text}",
            title="[bold blue]AI Command Plan[/bold blue]",
            border_style="blue"
        )
        
        self.console.print(panel)
    
    def _execute_command_sequence(self, commands: List[str]) -> bool:
        """Execute a sequence of commands."""
        success = True
        
        for i, command in enumerate(commands, 1):
            self.console.print(f"[dim]Executing {i}/{len(commands)}: {command}[/dim]")
            
            # Parse command
            parts = command.split()
            if not parts:
                continue
            
            cmd_name, *args = parts
            
            # Get command handler
            if cmd_name not in self.command_registry:
                self.console.print(f"[red]Unknown command: {cmd_name}[/red]")
                success = False
                continue
            
            # Execute command
            try:
                cmd_success = self.command_registry[cmd_name].execute(args)
                if not cmd_success:
                    success = False
                    if cmd_name == 'exit':
                        break  # Exit command should stop execution
            except Exception as e:
                self.console.print(f"[red]Error executing {cmd_name}: {e}[/red]")
                success = False
        
        if success:
            self.console.print("[green]All commands executed successfully[/green]")
        else:
            self.console.print("[yellow]Some commands failed[/yellow]")
        
        return success
    
    def help(self) -> str:
        return "ai <natural language> - Execute commands using natural language (requires Google AI API key)"


# Command aliases for natural language activation
class AskCommand(AICommand):
    """Alias for AI command with 'ask' keyword."""
    
    def help(self) -> str:
        return "ask <natural language> - Ask AI to perform a task using natural language"


class DoCommand(AICommand):
    """Alias for AI command with 'do' keyword."""
    
    def help(self) -> str:
        return "do <natural language> - Tell AI to do something using natural language"