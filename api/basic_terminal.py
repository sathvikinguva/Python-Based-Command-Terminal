"""
Web terminal with AI integration for Vercel deployment.
"""

from flask import Flask, render_template, request, jsonify
import os
import re
from datetime import datetime, timezone, timedelta

# AI Integration
try:
    import google.generativeai as genai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

app = Flask(__name__, template_folder='../templates', static_folder='../static')

class AITerminal:
    def __init__(self):
        self.current_directory = '/tmp'
        self.command_history = []
        self.file_storage = {}  # In-memory file storage for serverless environment
        
        # Setup AI
        self.ai_enabled = False
        if AI_AVAILABLE:
            api_key = os.environ.get('GOOGLE_API_KEY')
            if api_key:
                try:
                    genai.configure(api_key=api_key)
                    self.model = genai.GenerativeModel('gemini-pro')
                    self.ai_enabled = True
                except Exception as e:
                    print(f"AI setup failed: {e}")
        
        # Create working directory and essential subdirectories
        try:
            os.makedirs(self.current_directory, exist_ok=True)
            os.chdir(self.current_directory)
            
            # Create PyTerm directories
            os.makedirs('.recycle_bin', exist_ok=True)
            
            # Create history file
            if not os.path.exists('.pyterm_history'):
                with open('.pyterm_history', 'w') as f:
                    f.write("# PyTerm Command History\n")
                    f.write("# Web Terminal Session\n")
                    
        except:
            self.current_directory = os.getcwd()
    
    def parse_natural_language(self, text):
        """Convert natural language to terminal commands."""
        if not self.ai_enabled:
            return self._fallback_parse(text)
        
        try:
            prompt = f"""
Convert this natural language request to a terminal command:
"{text}"

Available commands: pwd, ls, cd, mkdir, echo, help, touch, write, python, edit
For Python code with multiple lines, use \\n for newlines in write commands.

Reply ONLY with the terminal command, nothing else.

Examples:
"show current directory" -> pwd
"list files" -> ls
"create folder test" -> mkdir test
"change to directory home" -> cd home
"display hello world" -> echo hello world
"create python file hello.py" -> touch hello.py
"write hello world program" -> write hello.py "print('Hello, World!')"
"write calculator program" -> write calculator.py "def add(a, b):\\n    return a + b\\n\\nprint(add(5, 3))"
"create fibonacci program" -> write fibonacci.py "def fibonacci(n):\\n    if n <= 1:\\n        return n\\n    return fibonacci(n-1) + fibonacci(n-2)\\n\\nprint(fibonacci(10))"

Command:"""
            
            response = self.model.generate_content(prompt)
            command = response.text.strip()
            
            # Basic validation
            valid_cmds = ['pwd', 'ls', 'cd', 'mkdir', 'echo', 'help', 'touch', 'write', 'python', 'edit', 'cat', 'rm']
            if any(command.startswith(cmd) for cmd in valid_cmds):
                return command
            else:
                return self._fallback_parse(text)
                
        except Exception as e:
            return self._fallback_parse(text)
    
    def _fallback_parse(self, text):
        """Fallback natural language parsing."""
        text = text.lower()
        
        # Python development commands
        if any(phrase in text for phrase in ['create python', 'make python', 'new python']) and 'file' in text:
            # Extract filename
            words = text.split()
            for i, word in enumerate(words):
                if word in ['file', 'script'] and i + 1 < len(words):
                    filename = words[i + 1]
                    if not filename.endswith('.py'):
                        filename += '.py'
                    return f'touch {filename}'
            return 'touch script.py'
            
        elif any(phrase in text for phrase in ['run python', 'execute python', 'python run']):
            # Extract filename
            words = text.split()
            for word in words:
                if word.endswith('.py'):
                    return f'python {word}'
            return 'python script.py'
            
        elif any(phrase in text for phrase in ['write', 'create']) and any(phrase in text for phrase in ['hello world', 'hello', 'program', 'script']):
            # Handle requests to write hello world programs
            if 'hello world' in text:
                return 'write hello.py "print(\'Hello, World!\')"'
            elif 'fibonacci' in text:
                return 'write fibonacci.py "def fibonacci(n):\\n    if n <= 1:\\n        return n\\n    return fibonacci(n-1) + fibonacci(n-2)\\n\\nprint(fibonacci(10))"'
            elif 'calculator' in text:
                return 'write calculator.py "def add(a, b):\\n    return a + b\\n\\nprint(add(5, 3))"'
            else:
                return 'touch script.py'  # Create empty Python file for other programs
                
        elif any(phrase in text for phrase in ['write to', 'write code', 'add code']):
            # This would need more complex parsing for actual implementation
            return 'echo Use: write filename.py "your code here"'
        
        # File listing commands
        elif any(phrase in text for phrase in ['list', 'show files', 'display files', 'what files']):
            if 'all' in text or 'hidden' in text:
                return 'ls -a'
            return 'ls'
        
        # Directory commands
        elif any(phrase in text for phrase in ['current directory', 'where am i', 'show directory', 'pwd']):
            return 'pwd'
            
        # Create folder/directory
        elif any(phrase in text for phrase in ['create', 'make', 'new']) and any(phrase in text for phrase in ['folder', 'directory', 'dir']):
            # Extract folder name
            words = text.split()
            for i, word in enumerate(words):
                if word in ['folder', 'directory', 'dir'] and i + 1 < len(words):
                    return f'mkdir {words[i + 1]}'
            # Look for "called" or "named"
            for keyword in ['called', 'named']:
                if keyword in text:
                    idx = text.find(keyword)
                    remaining = text[idx + len(keyword):].strip()
                    if remaining:
                        folder_name = remaining.split()[0]
                        return f'mkdir {folder_name}'
            return 'mkdir newfolder'
            
        # Change directory
        elif any(phrase in text for phrase in ['change', 'go to', 'navigate to']) and any(phrase in text for phrase in ['directory', 'folder', 'dir']):
            # Extract directory name
            words = text.split()
            for i, word in enumerate(words):
                if word in ['to', 'directory', 'folder'] and i + 1 < len(words):
                    return f'cd {words[i + 1]}'
            return 'cd'
            
        # Delete/remove
        elif any(phrase in text for phrase in ['delete', 'remove', 'rm']):
            words = text.split()
            for i, word in enumerate(words):
                if word in ['delete', 'remove', 'rm'] and i + 1 < len(words):
                    return f'rm {words[i + 1]}'
            return 'rm'
            
        # View file contents
        elif any(phrase in text for phrase in ['show', 'display', 'read', 'view']) and any(phrase in text for phrase in ['file', 'content', 'code']):
            words = text.split()
            for word in words:
                if '.' in word:  # Likely a filename
                    return f'cat {word}'
            return 'cat'
            
        # System monitoring
        elif any(phrase in text for phrase in ['system', 'monitor', 'stats', 'performance', 'cpu', 'memory']):
            return 'monitor'
            
        # Help
        elif any(phrase in text for phrase in ['help', 'commands', 'what can you do']):
            return 'help'
            
        # Display/echo
        elif any(phrase in text for phrase in ['say', 'display', 'show', 'print', 'echo']):
            # Remove the command word and return the rest
            for cmd_word in ['say', 'display', 'show', 'print', 'echo']:
                if cmd_word in text:
                    remaining = text.replace(cmd_word, '', 1).strip()
                    if remaining:
                        return f'echo {remaining}'
            return f'echo {text}'
            
        else:
            return f'echo I understand: {text}'
    
    def log_command_to_history(self, command):
        """Log command to .pyterm_history file."""
        try:
            history_file = os.path.join(self.current_directory, '.pyterm_history')
            # Use IST time (UTC+5:30)
            utc_now = datetime.utcnow()
            ist_time = utc_now + timedelta(hours=5, minutes=30)
            timestamp = ist_time.strftime("%Y-%m-%d %H:%M:%S IST")
            
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {command}\n")
        except Exception as e:
            # Silently fail if history logging fails
            pass
    
    def execute_command(self, command):
        parts = command.strip().split()
        if not parts:
            return {'output': '', 'error': '', 'current_directory': self.current_directory, 'success': True}
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == 'pwd':
            return {'output': self.current_directory, 'error': '', 'current_directory': self.current_directory, 'success': True}
        
        elif cmd == 'ls':
            try:
                show_all = '-a' in args or '-la' in args or '-al' in args
                items = []
                
                # Get all items in directory
                all_items = os.listdir(self.current_directory)
                
                # Add files from memory storage (for serverless environments)
                memory_files = list(self.file_storage.keys())
                all_items.extend([f for f in memory_files if f not in all_items])
                
                # Filter hidden files if not showing all
                if not show_all:
                    all_items = [item for item in all_items if not item.startswith('.')]
                
                # Sort items
                all_items.sort()
                
                for item in all_items:
                    full_path = os.path.join(self.current_directory, item)
                    if os.path.isdir(full_path):
                        items.append(f"📁 {item}/")
                    elif item in self.file_storage:
                        items.append(f"🐍 {item} (in memory)")
                    else:
                        items.append(f"📄 {item}")
                
                output = '\n'.join(items) if items else "Directory is empty"
                return {'output': output, 'error': '', 'current_directory': self.current_directory, 'success': True}
            except Exception as e:
                return {'output': '', 'error': str(e), 'current_directory': self.current_directory, 'success': False}
        
        elif cmd == 'mkdir':
            if not args:
                return {'output': '', 'error': 'mkdir: missing directory name', 'current_directory': self.current_directory, 'success': False}
            try:
                os.makedirs(os.path.join(self.current_directory, args[0]), exist_ok=True)
                return {'output': f"Directory '{args[0]}' created", 'error': '', 'current_directory': self.current_directory, 'success': True}
            except Exception as e:
                return {'output': '', 'error': str(e), 'current_directory': self.current_directory, 'success': False}
        
        elif cmd == 'cd':
            target = args[0] if args else '/tmp'
            if not os.path.isabs(target):
                target = os.path.join(self.current_directory, target)
            try:
                target = os.path.abspath(target)
                if os.path.exists(target) and os.path.isdir(target):
                    os.chdir(target)
                    self.current_directory = target
                    return {'output': f"Changed to {target}", 'error': '', 'current_directory': self.current_directory, 'success': True}
                else:
                    return {'output': '', 'error': f"Directory not found: {target}", 'current_directory': self.current_directory, 'success': False}
            except Exception as e:
                return {'output': '', 'error': str(e), 'current_directory': self.current_directory, 'success': False}
        
        elif cmd in ['ask', 'ai', 'do']:
            # AI natural language command
            if not args:
                return {'output': '', 'error': 'Usage: ask/ai/do <natural language request>', 'current_directory': self.current_directory, 'success': False}
            
            nl_text = ' '.join(args)
            try:
                parsed_cmd = self.parse_natural_language(nl_text)
                ai_result = self.execute_command(parsed_cmd)
                
                # Check if a file was created and add helpful message
                additional_message = ""
                if ai_result.get('success'):
                    # Check if the command was creating a Python file
                    if parsed_cmd.startswith('touch ') and '.py' in parsed_cmd:
                        filename = parsed_cmd.split()[1]  # Get the filename
                        additional_message = f"\n💡 {filename} was created! Now you can:\n• Edit it: edit {filename}\n• Run it: python {filename}"
                    elif parsed_cmd.startswith('write ') and '.py' in parsed_cmd:
                        filename = parsed_cmd.split()[1]  # Get the filename  
                        additional_message = f"\n💡 {filename} was created! Now you can run the code: python {filename}"
                
                return {
                    'output': f"🤖 AI interpreted: '{nl_text}' → {parsed_cmd}\n" + 
                             "Executing command...\n" + 
                             ai_result['output'] + 
                             additional_message,
                    'error': ai_result.get('error', ''),
                    'current_directory': self.current_directory,
                    'success': True
                }
            except Exception as e:
                return {'output': '', 'error': f"AI error: {str(e)}", 'current_directory': self.current_directory, 'success': False}
        
        elif cmd in ['la', 'll']:
            # Detailed listing (like ls -la) - always show all files including hidden
            try:
                items = []
                all_items = os.listdir(self.current_directory)
                all_items.sort()
                
                for item in all_items:
                    full_path = os.path.join(self.current_directory, item)
                    if os.path.isdir(full_path):
                        items.append(f"📁 {item}/")
                    else:
                        try:
                            size = os.path.getsize(full_path)
                            items.append(f"📄 {item} ({size} bytes)")
                        except:
                            items.append(f"📄 {item}")
                
                output = '\n'.join(items) if items else "Directory is empty"
                return {'output': output, 'error': '', 'current_directory': self.current_directory, 'success': True}
            except Exception as e:
                return {'output': '', 'error': str(e), 'current_directory': self.current_directory, 'success': False}
        
        elif cmd == 'rm':
            # Remove files/directories - move to recycle bin
            if not args:
                return {'output': '', 'error': 'rm: missing file/directory name', 'current_directory': self.current_directory, 'success': False}
            
            try:
                target = os.path.join(self.current_directory, args[0])
                if os.path.exists(target):
                    # Create recycle bin if it doesn't exist
                    recycle_bin = os.path.join(self.current_directory, '.recycle_bin')
                    os.makedirs(recycle_bin, exist_ok=True)
                    
                    # Generate unique name in recycle bin
                    import time
                    timestamp = str(int(time.time()))
                    recycled_name = f"{args[0]}_{timestamp}"
                    recycled_path = os.path.join(recycle_bin, recycled_name)
                    
                    # Move to recycle bin
                    import shutil
                    if os.path.isdir(target):
                        shutil.move(target, recycled_path)
                        return {'output': f"Directory '{args[0]}' moved to recycle bin as '{recycled_name}'", 'error': '', 'current_directory': self.current_directory, 'success': True}
                    else:
                        shutil.move(target, recycled_path)
                        return {'output': f"File '{args[0]}' moved to recycle bin as '{recycled_name}'", 'error': '', 'current_directory': self.current_directory, 'success': True}
                else:
                    return {'output': '', 'error': f"File/directory not found: {args[0]}", 'current_directory': self.current_directory, 'success': False}
            except Exception as e:
                return {'output': '', 'error': f"Cannot remove: {str(e)}", 'current_directory': self.current_directory, 'success': False}
        
        elif cmd == 'cat':
            # Display file contents
            if not args:
                return {'output': '', 'error': 'cat: missing file name', 'current_directory': self.current_directory, 'success': False}
            
            try:
                filename = args[0]
                file_path = os.path.join(self.current_directory, filename)
                
                # Check if file exists on disk
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return {'output': content if content else "(empty file)", 'error': '', 'current_directory': self.current_directory, 'success': True}
                # Check in-memory storage for serverless environments
                elif filename in self.file_storage:
                    content = self.file_storage[filename]
                    return {'output': content if content else "(empty file)", 'error': '', 'current_directory': self.current_directory, 'success': True}
                else:
                    return {'output': '', 'error': f"File not found: {filename}", 'current_directory': self.current_directory, 'success': False}
            except Exception as e:
                return {'output': '', 'error': f"Cannot read file: {str(e)}", 'current_directory': self.current_directory, 'success': False}
        
        elif cmd == 'touch':
            # Create empty files
            if not args:
                return {'output': '', 'error': 'touch: missing file name', 'current_directory': self.current_directory, 'success': False}
            
            try:
                filename = args[0]
                file_path = os.path.join(self.current_directory, filename)
                if not os.path.exists(file_path) and filename not in self.file_storage:
                    # Create empty file or Python template
                    if filename.endswith('.py'):
                        template_content = '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\n"""\nPython script created in PyTerm Web Terminal\n"""\n\ndef main():\n    print("Hello from PyTerm!")\n\nif __name__ == "__main__":\n    main()\n'
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(template_content)
                        # Also store in memory
                        self.file_storage[filename] = template_content
                        return {'output': f"Python file '{filename}' created with template", 'error': '', 'current_directory': self.current_directory, 'success': True}
                    else:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write('')
                        # Also store in memory
                        self.file_storage[filename] = ''
                        return {'output': f"File '{filename}' created", 'error': '', 'current_directory': self.current_directory, 'success': True}
                else:
                    return {'output': f"File '{filename}' already exists", 'error': '', 'current_directory': self.current_directory, 'success': True}
            except Exception as e:
                return {'output': '', 'error': f"Cannot create file: {str(e)}", 'current_directory': self.current_directory, 'success': False}
        
        elif cmd == 'write':
            # Write content to a file: write filename.py "content here"
            if len(args) < 2:
                return {'output': '', 'error': 'write: usage: write <filename> "<content>"', 'current_directory': self.current_directory, 'success': False}
            
            try:
                filename = args[0]
                # Join all remaining args as content (handling quotes)
                content = ' '.join(args[1:])
                
                # Remove surrounding quotes if present
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1]
                elif content.startswith("'") and content.endswith("'"):
                    content = content[1:-1]
                
                # Replace \\n with actual newlines
                content = content.replace('\\n', '\n')
                
                file_path = os.path.join(self.current_directory, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Also store in memory for serverless persistence
                self.file_storage[filename] = content
                
                return {'output': f"Content written to '{filename}'", 'error': '', 'current_directory': self.current_directory, 'success': True}
            except Exception as e:
                return {'output': '', 'error': f"Cannot write file: {str(e)}", 'current_directory': self.current_directory, 'success': False}
        
        elif cmd == 'append':
            # Append content to a file: append filename.py "content here"
            if len(args) < 2:
                return {'output': '', 'error': 'append: usage: append <filename> "<content>"', 'current_directory': self.current_directory, 'success': False}
            
            try:
                filename = args[0]
                content = ' '.join(args[1:])
                
                # Remove surrounding quotes if present
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1]
                elif content.startswith("'") and content.endswith("'"):
                    content = content[1:-1]
                
                # Replace \\n with actual newlines
                content = content.replace('\\n', '\n')
                
                file_path = os.path.join(self.current_directory, filename)
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(content)
                
                return {'output': f"Content appended to '{filename}'", 'error': '', 'current_directory': self.current_directory, 'success': True}
            except Exception as e:
                return {'output': '', 'error': f"Cannot append to file: {str(e)}", 'current_directory': self.current_directory, 'success': False}
        
        elif cmd == 'python' or cmd == 'python3':
            # Execute Python files
            if not args:
                return {'output': '', 'error': 'python: missing Python file name', 'current_directory': self.current_directory, 'success': False}
            
            try:
                python_file = args[0]
                file_path = os.path.join(self.current_directory, python_file)
                
                # Check if file exists on disk
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                # Check in-memory storage for serverless environments
                elif python_file in self.file_storage:
                    code = self.file_storage[python_file]
                else:
                    return {'output': '', 'error': f"Python file not found: {python_file}", 'current_directory': self.current_directory, 'success': False}
                
                if not python_file.endswith('.py'):
                    return {'output': '', 'error': f"File must be a Python file (.py): {python_file}", 'current_directory': self.current_directory, 'success': False}
                
                # Capture output
                import sys
                from io import StringIO
                
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                
                stdout_capture = StringIO()
                stderr_capture = StringIO()
                
                sys.stdout = stdout_capture
                sys.stderr = stderr_capture
                
                try:
                    # Execute the Python code
                    exec_globals = {'__name__': '__main__', '__file__': file_path}
                    exec(code, exec_globals)
                    
                    output = stdout_capture.getvalue()
                    error_output = stderr_capture.getvalue()
                    
                    result_output = f"🐍 Executed: {python_file}\n"
                    if output:
                        result_output += f"Output:\n{output}"
                    if error_output:
                        result_output += f"Errors:\n{error_output}"
                    
                    if not output and not error_output:
                        result_output += "Program executed successfully (no output)"
                    
                    return {
                        'output': result_output,
                        'error': '',
                        'current_directory': self.current_directory,
                        'success': True
                    }
                    
                except Exception as e:
                    return {
                        'output': f"🐍 Executed: {python_file}\nPython Error: {str(e)}",
                        'error': '',
                        'current_directory': self.current_directory,
                        'success': False
                    }
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    
            except Exception as e:
                return {'output': '', 'error': f"Cannot execute Python file: {str(e)}", 'current_directory': self.current_directory, 'success': False}
        
        elif cmd == 'run':
            # Alternative command to run Python files: run filename.py
            if not args:
                return {'output': '', 'error': 'run: missing file name', 'current_directory': self.current_directory, 'success': False}
            
            # Add .py extension if not present
            filename = args[0]
            if not filename.endswith('.py'):
                filename += '.py'
            
            # Call the python command
            return self.execute_command(f'python {filename}')
        
        elif cmd == 'edit':
            # Simple edit command for Python files
            if not args:
                return {'output': '', 'error': 'edit: missing file name', 'current_directory': self.current_directory, 'success': False}
            
            filename = args[0]
            file_path = os.path.join(self.current_directory, filename)
            
            # Check if file exists, if not create it with Python template
            if not os.path.exists(file_path):
                if filename.endswith('.py'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\n')
                        f.write('"""\nPython script created in PyTerm Web Terminal\n"""\n\n')
                        f.write('def main():\n')
                        f.write('    print("Hello from PyTerm!")\n\n')
                        f.write('if __name__ == "__main__":\n')
                        f.write('    main()\n')
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('')
            
            # Read existing content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            except:
                existing_content = ""
            
            # Return content for editing in a textarea
            return {
                'output': f"Editing file: {filename}\n\nType your code below and press Ctrl+S to save, or type 'exit' on a new line to close editor without saving.\n",
                'error': '',
                'current_directory': self.current_directory,
                'success': True,
                'edit_mode': True,
                'edit_data': {
                    'filename': filename,
                    'content': existing_content
                }
            }
        
        elif cmd == 'history':
            # Show command history
            try:
                history_file = os.path.join(self.current_directory, '.pyterm_history')
                if os.path.exists(history_file):
                    with open(history_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return {'output': content if content else "No history available", 'error': '', 'current_directory': self.current_directory, 'success': True}
                else:
                    return {'output': "No history file found", 'error': '', 'current_directory': self.current_directory, 'success': False}
            except Exception as e:
                return {'output': '', 'error': f"Cannot read history: {str(e)}", 'current_directory': self.current_directory, 'success': False}
        
        elif cmd == 'monitor':
            # System monitoring (simplified for serverless)
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Add current time information
                utc_time = datetime.utcnow()
                ist_time = utc_time + timedelta(hours=5, minutes=30)
                utc_str = utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                ist_str = ist_time.strftime("%Y-%m-%d %H:%M:%S IST")
                
                monitor_output = f"""🖥️  System Monitor:
                
Current Time (UTC): {utc_str}
Current Time (IST): {ist_str}

CPU Usage: {cpu_percent}%
Memory: {memory.percent}% used ({memory.used // 1024**3}GB / {memory.total // 1024**3}GB)
Disk Usage: {disk.percent}% used ({disk.used // 1024**3}GB / {disk.total // 1024**3}GB)

⚠️  Note: Running in serverless environment - limited system access"""
                
                return {'output': monitor_output, 'error': '', 'current_directory': self.current_directory, 'success': True}
            except ImportError:
                utc_time = datetime.utcnow()
                ist_time = utc_time + timedelta(hours=5, minutes=30)
                utc_str = utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                ist_str = ist_time.strftime("%Y-%m-%d %H:%M:%S IST")
                return {
                    'output': f'🖥️  System Monitor (Basic):\n\nCurrent Time (UTC): {utc_str}\nCurrent Time (IST): {ist_str}\n\nRunning in serverless environment\nLimited system information available\n\nProcess ID: ' + str(os.getpid()),
                    'error': '',
                    'current_directory': self.current_directory,
                    'success': True
                }
            except Exception as e:
                return {'output': '', 'error': f"Monitor error: {str(e)}", 'current_directory': self.current_directory, 'success': False}
        
        elif cmd in ['exit', 'quit']:
            # Exit command (for web, just show message)
            return {
                'output': '👋 Thank you for using PyTerm Web Terminal!\n\nTo exit, simply close the browser tab or navigate away.',
                'error': '',
                'current_directory': self.current_directory,
                'success': True
            }
        
        elif cmd == 'help':
            ai_status = "✅ Available" if self.ai_enabled else "❌ Not available"
            help_text = f"""📋 Available Commands:

📁 File Operations:
• pwd - Print the current working directory
• ls - List directory contents
• ls -a - List all files including hidden files (.pyterm_history, .recycle_bin)
• la, ll - List all files with details (always shows hidden files)
• cd <dir> - Change current directory
• mkdir <name> - Create directories
• rm <file/dir> - Remove files and directories (moves to .recycle_bin)
• cat <file> - Display file contents
• history - Show command history (same as: cat .pyterm_history)

🐍 Python Development:
• touch <file.py> - Create new Python file with template
• touch <file> - Create empty file
• edit <file> - Edit file in multi-line editor
• write <file> "content" - Write content to file (single line)
• append <file> "content" - Append content to file
• python <file.py> - Execute Python file
• python3 <file.py> - Execute Python file (same as python)
• run <filename> - Execute Python file (adds .py if needed)

🤖 AI Commands (Google AI: {ai_status}):
• ask <request> - Ask AI to perform a task using natural language
• ai <request> - Execute commands using natural language (requires Google AI API key)
• do <request> - Tell AI to do something using natural language

🖥️  System:
• monitor - Show system information
• help - Show help for commands

🚪 Exit:
• exit - Exit the terminal
• quit - Exit the terminal

💬 Other:
• echo <text> - Display text

🌟 Python Examples:
touch calculator.py                      # Create Python file with template
edit calculator.py                       # Edit file in multi-line editor
python calculator.py                     # Run the Python file
run calculator                           # Alternative way to run calculator.py

🌟 Quick One-liner:
write hello.py "print('Hello World!')"   # Write simple code (single line)

🌟 AI + Python Examples:
ask create a python file that calculates fibonacci
ai write a hello world program
do create a calculator script

PyTerm Web Terminal - Python Development Environment 🐍"""
            return {'output': help_text, 'error': '', 'current_directory': self.current_directory, 'success': True}
        
        elif cmd == 'echo':
            text = ' '.join(args)
            return {'output': text, 'error': '', 'current_directory': self.current_directory, 'success': True}
        
        else:
            return {'output': '', 'error': f"Command not found: {cmd}. Type 'help' for available commands.", 'current_directory': self.current_directory, 'success': False}

terminal = AITerminal()

@app.route('/')
def index():
    return render_template('simple_terminal.html')

@app.route('/api/execute', methods=['POST'])
def execute_command():
    try:
        data = request.get_json()
        command = data.get('command', '').strip()
        
        if command:
            # Log command to history file
            terminal.log_command_to_history(command)
            
            # Add to memory history
            terminal.command_history.append({
                'command': command,
                'timestamp': datetime.now().isoformat()
            })
        
        result = terminal.execute_command(command)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'output': '',
            'error': f"Server error: {str(e)}",
            'current_directory': terminal.current_directory,
            'success': False
        })

@app.route('/api/save', methods=['POST'])
def save_file():
    try:
        data = request.get_json()
        filename = data.get('filename', '')
        content = data.get('content', '')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': 'No filename provided'
            })
        
        file_path = os.path.join(terminal.current_directory, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            'success': True,
            'message': f"File '{filename}' saved successfully"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Cannot save file: {str(e)}"
        })

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'active',
        'current_directory': terminal.current_directory,
        'history_count': len(terminal.command_history)
    })

# For Vercel
app_instance = app