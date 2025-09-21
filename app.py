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
from ai_service import ai_service

app = Flask(__name__)
app.config['SECRET_KEY'] = 'terminal_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables for command history and current directory
command_history = []
current_directory = os.getcwd()
history_index = -1

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

            # Basic command validation: block dangerous commands
            forbidden = ['rm -rf /', 'shutdown', 'reboot', 'poweroff', ':(){:|:&};:']
            for bad in forbidden:
                if bad in command:
                    return {'type': 'error', 'output': 'Dangerous command blocked.'}

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
                return {'type': 'error', 'output': 'Command timed out'}
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
    
    def add_output(self, text, output_type='output'):
        """Add output to terminal (for internal use)"""
        # This method is used internally by the terminal backend
        pass
    
    def handle_cd(self, command):
        """Handle cd command"""
        try:
            path = command[3:].strip()
            if not path:
                path = os.path.expanduser('~')
            
            if path == '..':
                new_path = os.path.dirname(self.current_dir)
            elif path.startswith('/') or path.startswith('C:'):
                new_path = path
            else:
                new_path = os.path.join(self.current_dir, path)
            
            if os.path.exists(new_path) and os.path.isdir(new_path):
                self.current_dir = os.path.abspath(new_path)
                return {'type': 'output', 'output': ''}
            else:
                return {'type': 'error', 'output': f'cd: {path}: No such file or directory'}
        except Exception as e:
            return {'type': 'error', 'output': f'cd error: {str(e)}'}
    
    def handle_ls(self, command):
        """Handle ls command"""
        try:
            args = command.split()[1:] if len(command.split()) > 1 else []
            path = self.current_dir
            
            if args and not args[0].startswith('-'):
                path = os.path.join(self.current_dir, args[0])
            
            if not os.path.exists(path):
                return {'type': 'error', 'output': f'ls: {path}: No such file or directory'}
            
            if not os.path.isdir(path):
                return {'type': 'error', 'output': f'ls: {path}: Not a directory'}
            
            files = os.listdir(path)
            if '-l' in args:
                # Long format
                output_lines = []
                for file in files:
                    file_path = os.path.join(path, file)
                    stat = os.stat(file_path)
                    size = stat.st_size
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%b %d %H:%M')
                    file_type = 'd' if os.path.isdir(file_path) else '-'
                    output_lines.append(f"{file_type} {size:>8} {mtime} {file}")
                return {'type': 'output', 'output': '\n'.join(output_lines)}
            else:
                # Simple format
                return {'type': 'output', 'output': '  '.join(files)}
        except Exception as e:
            return {'type': 'error', 'output': f'ls error: {str(e)}'}
    
    def handle_mkdir(self, command):
        """Handle mkdir command"""
        try:
            dir_name = command[6:].strip()
            if not dir_name:
                return {'type': 'error', 'output': 'mkdir: missing operand'}
            
            dir_path = os.path.join(self.current_dir, dir_name)
            os.makedirs(dir_path, exist_ok=True)
            return {'type': 'output', 'output': ''}
        except Exception as e:
            return {'type': 'error', 'output': f'mkdir error: {str(e)}'}
    
    def handle_rm(self, command):
        """Handle rm command"""
        try:
            args = command.split()[1:]
            if not args:
                return {'type': 'error', 'output': 'rm: missing operand'}
            
            file_path = os.path.join(self.current_dir, args[0])
            if os.path.exists(file_path):
                if os.path.isdir(file_path):
                    if '-r' in args or '-rf' in args:
                        shutil.rmtree(file_path)
                    else:
                        return {'type': 'error', 'output': f'rm: {args[0]}: is a directory'}
                else:
                    os.remove(file_path)
                return {'type': 'output', 'output': ''}
            else:
                return {'type': 'error', 'output': f'rm: {args[0]}: No such file or directory'}
        except Exception as e:
            return {'type': 'error', 'output': f'rm error: {str(e)}'}
    
    def handle_cat(self, command):
        """Handle cat command"""
        try:
            file_name = command[4:].strip()
            if not file_name:
                return {'type': 'error', 'output': 'cat: missing operand'}
            
            file_path = os.path.join(self.current_dir, file_name)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {'type': 'output', 'output': content}
            else:
                return {'type': 'error', 'output': f'cat: {file_name}: No such file or directory'}
        except Exception as e:
            return {'type': 'error', 'output': f'cat error: {str(e)}'}
    
    def handle_ps(self):
        """Handle ps command - show running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            output = f"{'PID':<8} {'NAME':<20} {'CPU%':<8} {'MEM%':<8}\n"
            output += "-" * 50 + "\n"
            for proc in processes[:20]:  # Show top 20 processes
                output += f"{proc['pid']:<8} {proc['name']:<20} {proc['cpu_percent']:<8.1f} {proc['memory_percent']:<8.1f}\n"
            
            return {'type': 'output', 'output': output}
        except Exception as e:
            return {'type': 'error', 'output': f'ps error: {str(e)}'}
    
    def handle_top(self):
        """Handle top command - system overview"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            output = f"System Overview:\n"
            output += f"CPU Usage: {cpu_percent}%\n"
            output += f"Memory: {memory.percent}% used ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)\n"
            output += f"Disk: {disk.percent}% used ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)\n"
            
            return {'type': 'output', 'output': output}
        except Exception as e:
            return {'type': 'error', 'output': f'top error: {str(e)}'}
    
    def handle_df(self):
        """Handle df command - disk usage"""
        try:
            partitions = psutil.disk_partitions()
            output = f"{'Filesystem':<20} {'Size':<10} {'Used':<10} {'Available':<10} {'Use%':<8} {'Mounted on'}\n"
            output += "-" * 80 + "\n"
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    total = usage.total // (1024**3)
                    used = usage.used // (1024**3)
                    free = usage.free // (1024**3)
                    percent = (usage.used / usage.total) * 100
                    
                    output += f"{partition.device:<20} {total:<10}G {used:<10}G {free:<10}G {percent:<7.1f}% {partition.mountpoint}\n"
                except PermissionError:
                    continue
            
            return {'type': 'output', 'output': output}
        except Exception as e:
            return {'type': 'error', 'output': f'df error: {str(e)}'}
    
    def handle_free(self):
        """Handle free command - memory usage"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            output = f"{'':<12} {'Total':<10} {'Used':<10} {'Free':<10} {'Shared':<10} {'Available':<10}\n"
            output += "-" * 70 + "\n"
            output += f"{'Mem':<12} {memory.total // (1024**2):<10} {memory.used // (1024**2):<10} {memory.available // (1024**2):<10} {0:<10} {memory.available // (1024**2):<10}\n"
            output += f"{'Swap':<12} {swap.total // (1024**2):<10} {swap.used // (1024**2):<10} {swap.free // (1024**2):<10} {0:<10} {0:<10}\n"
            
            return {'type': 'output', 'output': output}
        except Exception as e:
            return {'type': 'error', 'output': f'free error: {str(e)}'}
    
    def handle_ai_help(self):
        """Handle ai-help command"""
        help_text = """
Command Terminal Features:

Natural Language Commands:
• "list files" -> ls
• "create folder called test" -> mkdir test
• "go to documents" -> cd documents
• "show me running processes" -> ps
• "what's in this file" -> cat filename
• "delete the test folder" -> rm -r test
• "show system info" -> top

AI Features:
• Type natural language and AI will convert to commands
• Get command suggestions when unsure
• AI explains what commands do
• Smart command interpretation

Examples:
• "I want to see what files are here"
• "Create a new directory for my project"
• "Show me the system status"
• "Help me navigate to the desktop"

Type any natural language command to try it out!
        """
        return {'type': 'output', 'output': help_text}

# Initialize terminal backend
terminal = TerminalBackend()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    emit('terminal_output', {
        'type': 'welcome',
        'output': f'Welcome to Python Terminal!\nCurrent directory: {terminal.current_dir}\nType "help" for available commands.\n'
    })

@socketio.on('command')
def handle_command(data):
    command = data.get('command', '').strip()
    os_mode = data.get('os_mode', None)
    if not command:
        return
    # Add to history
    terminal.command_history.append(command)
    terminal.history_index = len(terminal.command_history) - 1
    # Set mode for this request if provided
    if os_mode:
        ai_service.set_mode(os_mode)
    # Execute command
    result = terminal.execute_command(command)
    # Send result back to client
    emit('terminal_output', result)

@socketio.on('get_history')
def handle_get_history():
    emit('command_history', {'history': terminal.command_history})

@socketio.on('get_system_info')
def handle_get_system_info():
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_info = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used': memory.used // (1024**3),
            'memory_total': memory.total // (1024**3),
            'disk_percent': disk.percent,
            'disk_used': disk.used // (1024**3),
            'disk_total': disk.total // (1024**3)
        }
        
        emit('system_info', system_info)
    except Exception as e:
        emit('system_info', {'error': str(e)})

@socketio.on('get_ai_suggestions')
def handle_get_ai_suggestions(data):
    partial_command = data.get('command', '')
    suggestions = ai_service.get_suggestions(partial_command)
    emit('ai_suggestions', {'suggestions': suggestions})

@socketio.on('interpret_natural_language')
def handle_interpret_natural_language(data):
    natural_language = data.get('command', '')
    result = ai_service.interpret_command(natural_language)
    emit('ai_interpretation', result)

@socketio.on('explain_command')
def handle_explain_command(data):
    command = data.get('command', '')
    explanation = ai_service.explain_command(command)
    emit('command_explanation', {'command': command, 'explanation': explanation})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
