from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import os
import psutil
import json
import shutil
from datetime import datetime
import threading
import queue
import time
import eventlet
import eventlet.wsgi

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'terminal_secret_key_fallback')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global variables for command history and current directory
command_history = []
current_directory = os.getcwd()
history_index = -1

class AIService:
    """AI service using pattern matching (no external API required)"""
    
    def __init__(self):
        self.mode = 'unix'  # Default mode
        
        # Simple command mappings for fallback
        self.command_mappings = {
            'list files': 'ls',
            'list directories': 'ls -la',
            'show files': 'ls',
            'current directory': 'pwd',
            'where am i': 'pwd',
            'change directory': 'cd',
            'go to': 'cd',
            'navigate to': 'cd',
            'make directory': 'mkdir',
            'create folder': 'mkdir',
            'create directory': 'mkdir',
            'remove file': 'rm',
            'delete file': 'rm',
            'remove directory': 'rm -r',
            'delete folder': 'rm -r',
            'show file content': 'cat',
            'read file': 'cat',
            'display file': 'cat',
            'running processes': 'ps',
            'system status': 'top',
            'disk usage': 'df',
            'memory usage': 'free',
            'help': 'help'
        }
    
    def set_mode(self, mode):
        """Set the operating system mode"""
        self.mode = mode
    
    def interpret_command(self, natural_language):
        """Convert natural language to terminal command"""
        nl_lower = natural_language.lower().strip()
        
        # Pattern matching for natural language commands
        for phrase, command in self.command_mappings.items():
            if phrase in nl_lower:
                return {
                    'command': command,
                    'confidence': 0.8,
                    'explanation': f'Interpreted "{natural_language}" as "{command}"'
                }
        
        # Try to extract directory/file names for commands
        if 'go to' in nl_lower or 'navigate to' in nl_lower or 'change to' in nl_lower:
            # Extract the directory name
            words = nl_lower.replace('go to', '').replace('navigate to', '').replace('change to', '').strip()
            if words:
                return {
                    'command': f'cd {words}',
                    'confidence': 0.9,
                    'explanation': f'Interpreted as change directory to "{words}"'
                }
        
        if 'create' in nl_lower and ('folder' in nl_lower or 'directory' in nl_lower):
            # Extract folder name
            words = nl_lower.split()
            if 'called' in words:
                idx = words.index('called')
                if idx + 1 < len(words):
                    folder_name = words[idx + 1]
                    return {
                        'command': f'mkdir {folder_name}',
                        'confidence': 0.9,
                        'explanation': f'Interpreted as create directory "{folder_name}"'
                    }
        
        return {
            'command': natural_language,
            'confidence': 0.1,
            'explanation': 'Could not interpret command'
        }
    
    def get_suggestions(self, partial_command):
        """Get command suggestions"""
        suggestions = []
        pc_lower = partial_command.lower()
        
        common_commands = ['ls', 'cd', 'pwd', 'mkdir', 'rm', 'cat', 'ps', 'top', 'df', 'free', 'clear', 'history']
        
        for cmd in common_commands:
            if cmd.startswith(pc_lower):
                suggestions.append(cmd)
        
        return suggestions[:5]
    
    def explain_command(self, command):
        """Explain what a command does"""
        explanations = {
            'ls': 'List directory contents',
            'cd': 'Change directory',
            'pwd': 'Print working directory',
            'mkdir': 'Create directory',
            'rm': 'Remove files or directories',
            'cat': 'Display file contents',
            'ps': 'Show running processes',
            'top': 'Display system resource usage',
            'df': 'Show disk usage',
            'free': 'Show memory usage',
            'clear': 'Clear terminal screen',
            'history': 'Show command history'
        }
        
        cmd_base = command.split()[0] if command.split() else command
        return explanations.get(cmd_base, f'Command: {command}')

# Initialize AI service
ai_service = AIService()

class TerminalBackend:
    def __init__(self):
        self.current_dir = os.getcwd()
        self.command_history = []
        self.history_index = -1
    
    def execute_command(self, command):
        """Execute terminal commands and return output (with streaming and improved security)"""
        try:
            # Check if this is a natural language command
            if self._is_natural_language(command):
                ai_result = ai_service.interpret_command(command)
                if ai_result['confidence'] > 0.5:
                    interpretation_msg = f"🤖 AI interpreted: '{command}' → '{ai_result['command']}'"
                    return {
                        'type': 'ai_interpretation',
                        'output': interpretation_msg,
                        'interpreted_command': ai_result['command'],
                        'original_command': command
                    }
                else:
                    suggestions = ai_service.get_suggestions(command)
                    if suggestions:
                        return {'type': 'suggestion', 'output': f"Did you mean: {', '.join(suggestions[:3])}?", 'suggestions': suggestions}
                    else:
                        return {'type': 'error', 'output': f"Could not understand: '{command}'. Type 'help' for available commands."}

            # Handle special commands
            if command.strip() == 'clear':
                return {'type': 'clear', 'output': ''}
            elif command.strip() == 'history':
                return {'type': 'output', 'output': '\n'.join([f"{i+1}: {cmd}" for i, cmd in enumerate(self.command_history)])}
            elif command.startswith('cd '):
                return self.handle_cd(command)
            elif command.strip() == 'pwd':
                return {'type': 'output', 'output': self.current_dir}
            elif command.startswith('ls'):
                return self.handle_ls(command)
            elif command.startswith('mkdir '):
                return self.handle_mkdir(command)
            elif command.startswith('rm '):
                return self.handle_rm(command)
            elif command.startswith('cat '):
                return self.handle_cat(command)
            elif command.strip() == 'ps':
                return self.handle_ps()
            elif command.strip() == 'top':
                return self.handle_top()
            elif command.strip() == 'df':
                return self.handle_df()
            elif command.strip() == 'free':
                return self.handle_free()
            elif command.strip() == 'ai-help':
                return self.handle_ai_help()
            elif command.strip() == 'help':
                return self.handle_help()

            # Basic command validation: block dangerous commands
            forbidden = ['rm -rf /', 'shutdown', 'reboot', 'poweroff', ':(){:|:&};:', 'format', 'fdisk', 'mkfs']
            for bad in forbidden:
                if bad in command.lower():
                    return {'type': 'error', 'output': 'Dangerous command blocked for security.'}

            # Use Popen for real-time output streaming
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.current_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            output_lines = []
            try:
                # Read output line by line (simulate streaming)
                for line in iter(process.stdout.readline, ''):
                    if not line:
                        break
                    output_lines.append(line.rstrip())
                process.stdout.close()
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                return {'type': 'error', 'output': 'Command timed out (15s limit)'}
            except Exception as e:
                process.kill()
                return {'type': 'error', 'output': f'Error: {str(e)}'}

            output = '\n'.join(output_lines)
            return {'type': 'output', 'output': output, 'return_code': process.returncode}
        except Exception as e:
            return {'type': 'error', 'output': f'Error: {str(e)}'}
    
    def _is_natural_language(self, command):
        """Check if the command appears to be natural language"""
        # If it's already a known command, it's not natural language
        known_commands = ['ls', 'cd', 'pwd', 'mkdir', 'rm', 'cat', 'ps', 'top', 'df', 'free', 'clear', 'help', 'history', 'ai-help']
        if command.strip().split()[0] in known_commands:
            return False
        
        # Check for natural language indicators
        natural_indicators = [
            'list', 'show', 'create', 'make', 'delete', 'remove', 'go to', 'navigate',
            'change to', 'display', 'read', 'what', 'how', 'can you', 'please',
            'i want', 'i need', 'help me', 'tell me'
        ]
        
        command_lower = command.lower()
        return any(indicator in command_lower for indicator in natural_indicators)
    
    def handle_help(self):
        """Handle help command"""
        help_text = """
Available Commands:
• ls [path] - List directory contents
• cd <path> - Change directory
• pwd - Show current directory
• mkdir <name> - Create directory
• rm <file> - Remove file
• rm -r <dir> - Remove directory
• cat <file> - Display file contents
• ps - Show running processes
• top - System resource usage
• df - Disk usage
• free - Memory usage
• clear - Clear screen
• history - Command history
• ai-help - AI features help
• help - Show this help

Try natural language commands like:
• "list files in current directory"
• "create a folder called test"
• "show me system status"
        """
        return {'type': 'output', 'output': help_text}
    
    def handle_cd(self, command):
        """Handle cd command"""
        try:
            path = command[3:].strip()
            if not path:
                path = os.path.expanduser('~')
            
            if path == '..':
                new_path = os.path.dirname(self.current_dir)
            elif path.startswith('/') or (len(path) > 1 and path[1] == ':'):  # Unix absolute or Windows drive
                new_path = path
            else:
                new_path = os.path.join(self.current_dir, path)
            
            if os.path.exists(new_path) and os.path.isdir(new_path):
                self.current_dir = os.path.abspath(new_path)
                return {'type': 'output', 'output': f'Changed to: {self.current_dir}'}
            else:
                return {'type': 'error', 'output': f'cd: {path}: No such file or directory'}
        except Exception as e:
            return {'type': 'error', 'output': f'cd error: {str(e)}'}
    
    def handle_ls(self, command):
        """Handle ls command"""
        try:
            args = command.split()[1:] if len(command.split()) > 1 else []
            path = self.current_dir
            
            # Check if there's a path argument (not a flag)
            for arg in args:
                if not arg.startswith('-'):
                    path = os.path.join(self.current_dir, arg) if not os.path.isabs(arg) else arg
                    break
            
            if not os.path.exists(path):
                return {'type': 'error', 'output': f'ls: {path}: No such file or directory'}
            
            if not os.path.isdir(path):
                return {'type': 'output', 'output': os.path.basename(path)}
            
            try:
                files = os.listdir(path)
            except PermissionError:
                return {'type': 'error', 'output': f'ls: {path}: Permission denied'}
            
            files.sort()  # Sort files alphabetically
            
            if '-l' in args:
                # Long format
                output_lines = []
                for file in files:
                    file_path = os.path.join(path, file)
                    try:
                        stat = os.stat(file_path)
                        size = stat.st_size
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%b %d %H:%M')
                        file_type = 'd' if os.path.isdir(file_path) else '-'
                        perms = 'rwxrwxrwx' if os.access(file_path, os.R_OK | os.W_OK | os.X_OK) else 'r--r--r--'
                        output_lines.append(f"{file_type}{perms} {size:>8} {mtime} {file}")
                    except (OSError, PermissionError):
                        output_lines.append(f"?????????? {0:>8} ??? ?? ??:?? {file}")
                return {'type': 'output', 'output': '\n'.join(output_lines)}
            else:
                # Simple format - show in columns
                if not files:
                    return {'type': 'output', 'output': ''}
                return {'type': 'output', 'output': '  '.join(files)}
        except Exception as e:
            return {'type': 'error', 'output': f'ls error: {str(e)}'}
    
    def handle_mkdir(self, command):
        """Handle mkdir command"""
        try:
            dir_name = command[6:].strip()
            if not dir_name:
                return {'type': 'error', 'output': 'mkdir: missing operand'}
            
            dir_path = os.path.join(self.current_dir, dir_name) if not os.path.isabs(dir_name) else dir_name
            os.makedirs(dir_path, exist_ok=True)
            return {'type': 'output', 'output': f'Directory created: {dir_name}'}
        except Exception as e:
            return {'type': 'error', 'output': f'mkdir error: {str(e)}'}
    
    def handle_rm(self, command):
        """Handle rm command"""
        try:
            args = command.split()[1:]
            if not args:
                return {'type': 'error', 'output': 'rm: missing operand'}
            
            # Filter out flags to get the file/directory name
            file_args = [arg for arg in args if not arg.startswith('-')]
            if not file_args:
                return {'type': 'error', 'output': 'rm: missing file operand'}
            
            file_path = os.path.join(self.current_dir, file_args[0]) if not os.path.isabs(file_args[0]) else file_args[0]
            
            if not os.path.exists(file_path):
                return {'type': 'error', 'output': f'rm: {file_args[0]}: No such file or directory'}
            
            if os.path.isdir(file_path):
                if '-r' in args or '-rf' in args or '--recursive' in args:
                    shutil.rmtree(file_path)
                    return {'type': 'output', 'output': f'Directory removed: {file_args[0]}'}
                else:
                    return {'type': 'error', 'output': f'rm: {file_args[0]}: is a directory (use -r for directories)'}
            else:
                os.remove(file_path)
                return {'type': 'output', 'output': f'File removed: {file_args[0]}'}
        except Exception as e:
            return {'type': 'error', 'output': f'rm error: {str(e)}'}
    
    def handle_cat(self, command):
        """Handle cat command"""
        try:
            file_name = command[4:].strip()
            if not file_name:
                return {'type': 'error', 'output': 'cat: missing operand'}
            
            file_path = os.path.join(self.current_dir, file_name) if not os.path.isabs(file_name) else file_name
            
            if not os.path.exists(file_path):
                return {'type': 'error', 'output': f'cat: {file_name}: No such file or directory'}
            
            if os.path.isdir(file_path):
                return {'type': 'error', 'output': f'cat: {file_name}: Is a directory'}
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Limit output size for safety
                    if len(content) > 10000:
                        content = content[:10000] + '\n... (output truncated)'
                return {'type': 'output', 'output': content}
            except UnicodeDecodeError:
                return {'type': 'error', 'output': f'cat: {file_name}: Binary file (not displayed)'}
        except Exception as e:
            return {'type': 'error', 'output': f'cat error: {str(e)}'}
    
    def handle_ps(self):
        """Handle ps command - show running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
            
            output = f"{'PID':<8} {'NAME':<25} {'CPU%':<8} {'MEM%':<8}\n"
            output += "-" * 55 + "\n"
            
            for proc in processes[:20]:  # Show top 20 processes
                pid = proc['pid']
                name = (proc['name'][:22] + '...') if len(proc['name']) > 25 else proc['name']
                cpu = proc['cpu_percent'] or 0
                mem = proc['memory_percent'] or 0
                output += f"{pid:<8} {name:<25} {cpu:<7.1f}% {mem:<7.1f}%\n"
            
            return {'type': 'output', 'output': output}
        except Exception as e:
            return {'type': 'error', 'output': f'ps error: {str(e)}'}
    
    def handle_top(self):
        """Handle top command - system overview"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            output = f"System Overview:\n"
            output += f"{'='*50}\n"
            output += f"Uptime: {datetime.now() - boot_time}\n"
            output += f"CPU Usage: {cpu_percent:.1f}%\n"
            output += f"Memory: {memory.percent:.1f}% used ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)\n"
            output += f"Disk: {disk.percent:.1f}% used ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)\n"
            output += f"Available Memory: {memory.available // (1024**3):.1f}GB\n"
            
            return {'type': 'output', 'output': output}
        except Exception as e:
            return {'type': 'error', 'output': f'top error: {str(e)}'}
    
    def handle_df(self):
        """Handle df command - disk usage"""
        try:
            partitions = psutil.disk_partitions()
            output = f"{'Filesystem':<20} {'Size':<8} {'Used':<8} {'Avail':<8} {'Use%':<6} {'Mounted on'}\n"
            output += "-" * 70 + "\n"
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    total = usage.total // (1024**3)
                    used = usage.used // (1024**3)
                    free = usage.free // (1024**3)
                    percent = (usage.used / usage.total) * 100 if usage.total > 0 else 0
                    
                    device = partition.device[:17] + '...' if len(partition.device) > 20 else partition.device
                    mountpoint = partition.mountpoint[:15] + '...' if len(partition.mountpoint) > 18 else partition.mountpoint
                    
                    output += f"{device:<20} {total:<7}G {used:<7}G {free:<7}G {percent:<5.1f}% {mountpoint}\n"
                except (PermissionError, OSError):
                    continue
            
            return {'type': 'output', 'output': output}
        except Exception as e:
            return {'type': 'error', 'output': f'df error: {str(e)}'}
    
    def handle_free(self):
        """Handle free command - memory usage"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            output = f"
