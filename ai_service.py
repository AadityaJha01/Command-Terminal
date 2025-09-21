import openai
import os
import re
from typing import Dict, List, Optional
import json

class AICommandInterpreter:
    def __init__(self):
        # Initialize OpenAI client
        self.client = None
        self.setup_openai()
        
        # Command patterns for fallback
        self.command_patterns = {
            'list_files': ['list files', 'show files', 'what files are here', 'ls', 'list all', 'show all files'],
            'change_directory': ['go to', 'navigate to', 'change to', 'cd', 'go into', 'enter'],
            'create_directory': ['create folder', 'make directory', 'new folder', 'mkdir', 'create directory', 'make folder', 'create', 'make'],
            'delete_file': ['delete file', 'remove file', 'rm', 'delete folder', 'remove folder', 'delete directory', 'delete', 'remove'],
            'show_content': ['show content', 'display file', 'read file', 'cat', 'show me what', 'what\'s in'],
            'system_info': ['system info', 'show system', 'top', 'ps', 'processes', 'running processes'],
            'clear_screen': ['clear screen', 'clear terminal', 'clear'],
            'help': ['help', 'what can I do', 'commands', 'show help']
        }
        
        # Common command mappings
        self.command_mappings = {
            'list_files': 'ls',
            'change_directory': 'cd',
            'create_directory': 'mkdir',
            'delete_file': 'rm',
            'show_content': 'cat',
            'system_info': 'top',
            'clear_screen': 'clear',
            'help': 'help'
        }
    
    def setup_openai(self):
        """Setup OpenAI client with API key from environment"""
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.client = openai.OpenAI(api_key=api_key)
        else:
            print("Warning: OPENAI_API_KEY not found. AI features will use fallback patterns.")
    
    def interpret_command(self, natural_language: str) -> Dict:
        """
        Interpret natural language command and return structured response
        """
        natural_language = natural_language.strip().lower()
        
        # First try AI interpretation if available
        if self.client:
            ai_result = self._ai_interpret(natural_language)
            if ai_result:
                return ai_result
        
        # Fallback to pattern matching
        return self._pattern_interpret(natural_language)
    
    def _ai_interpret(self, natural_language: str) -> Optional[Dict]:
        """Use OpenAI to interpret natural language commands"""
        try:
            prompt = f"""
            You are a terminal command interpreter. Convert natural language requests into complete terminal commands with all necessary parameters.
            
            Available commands: ls, cd, pwd, mkdir, rm, cat, ps, top, df, free, clear, history, help
            
            Rules:
            1. Return ONLY the complete command with all parameters, no explanations
            2. Extract file/folder names from the natural language and include them in the command
            3. Use appropriate flags (e.g., -r for recursive operations, -l for detailed listings)
            4. For directory changes, use 'cd' with the extracted directory name
            5. For file operations, include the extracted file/folder names
            6. If multiple files/folders are mentioned, handle them appropriately
            7. Use relative paths when possible
            
            Examples:
            - "create a folder called test" → "mkdir test"
            - "create a folder called test 2" → "mkdir test2"
            - "list all files" → "ls -la"
            - "go to documents folder" → "cd documents"
            - "delete the test folder" → "rm -r test"
            - "show me what's in file.txt" → "cat file.txt"
            - "create directories for my project" → "mkdir project"
            
            Natural language: "{natural_language}"
            
            Complete command:"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful terminal command interpreter. Always extract file/folder names and create complete commands."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.1
            )
            
            command = response.choices[0].message.content.strip()
            
            # Clean up the command (remove any extra text)
            command = command.split('\n')[0].strip()
            
            # Validate the command
            if self._is_valid_command(command):
                return {
                    'command': command,
                    'confidence': 0.9,
                    'method': 'ai',
                    'original': natural_language
                }
            
        except Exception as e:
            print(f"AI interpretation error: {e}")
        
        return None
    
    def _pattern_interpret(self, natural_language: str) -> Dict:
        """Fallback pattern matching for command interpretation"""
        confidence = 0.0
        command = ""
        
        # Check for direct command matches
        if natural_language in ['ls', 'cd', 'pwd', 'mkdir', 'rm', 'cat', 'ps', 'top', 'df', 'free', 'clear', 'help']:
            return {
                'command': natural_language,
                'confidence': 1.0,
                'method': 'direct',
                'original': natural_language
            }
        
        # Pattern matching with improved parameter extraction
        for intent, patterns in self.command_patterns.items():
            for pattern in patterns:
                if pattern in natural_language.lower():
                    base_command = self.command_mappings.get(intent, '')
                    
                    # Extract parameters with better regex patterns
                    if intent == 'change_directory':
                        # Extract directory name - improved patterns
                        dir_patterns = [
                            r'(?:go to|navigate to|change to|cd to)\s+([^\s]+)',
                            r'(?:to|into|in)\s+([^\s]+)',
                            r'(?:folder|directory)\s+([^\s]+)',
                            r'(?:go|navigate|change)\s+([^\s]+)'
                        ]
                        for dir_pattern in dir_patterns:
                            dir_match = re.search(dir_pattern, natural_language, re.IGNORECASE)
                            if dir_match:
                                command = f"{base_command} {dir_match.group(1)}"
                                break
                        if not command:
                            command = base_command
                            
                    elif intent == 'create_directory':
                        # Extract directory name - improved patterns
                        dir_patterns = [
                            r'(?:create|make)\s+(?:a\s+)?(?:folder|directory)\s+(?:called\s+)?([^\s]+(?:\s+[^\s]+)*)',
                            r'(?:new\s+)?(?:folder|directory)\s+(?:called\s+)?([^\s]+(?:\s+[^\s]+)*)',
                            r'(?:mkdir|create)\s+([^\s]+(?:\s+[^\s]+)*)',
                            r'(?:create|make)\s+([^\s]+(?:\s+[^\s]+)*)'
                        ]
                        for dir_pattern in dir_patterns:
                            dir_match = re.search(dir_pattern, natural_language, re.IGNORECASE)
                            if dir_match:
                                # Clean up the directory name (remove spaces, special chars)
                                dir_name = dir_match.group(1).strip().replace(' ', '_').replace('"', '').replace("'", '')
                                command = f"{base_command} {dir_name}"
                                break
                        if not command:
                            command = base_command
                            
                    elif intent == 'delete_file':
                        # Extract file/folder name - improved patterns
                        file_patterns = [
                            r'(?:delete|remove)\s+(?:the\s+)?(?:file|folder)\s+(?:called\s+)?([^\s]+(?:\s+[^\s]+)*)',
                            r'(?:rm|delete)\s+([^\s]+(?:\s+[^\s]+)*)',
                            r'(?:file|folder)\s+([^\s]+(?:\s+[^\s]+)*)'
                        ]
                        for file_pattern in file_patterns:
                            file_match = re.search(file_pattern, natural_language, re.IGNORECASE)
                            if file_match:
                                file_name = file_match.group(1).strip().replace('"', '').replace("'", '')
                                # Determine if it's a directory (add -r flag)
                                if 'folder' in natural_language.lower() or 'directory' in natural_language.lower():
                                    command = f"{base_command} -r {file_name}"
                                else:
                                    command = f"{base_command} {file_name}"
                                break
                        if not command:
                            command = base_command
                            
                    elif intent == 'show_content':
                        # Extract file name - improved patterns
                        file_patterns = [
                            r'(?:show|display|read)\s+(?:me\s+)?(?:the\s+)?(?:content\s+of\s+)?(?:file\s+)?([^\s]+(?:\s+[^\s]+)*)',
                            r'(?:what\'s\s+in|what\s+is\s+in)\s+([^\s]+(?:\s+[^\s]+)*)',
                            r'(?:cat|show)\s+([^\s]+(?:\s+[^\s]+)*)'
                        ]
                        for file_pattern in file_patterns:
                            file_match = re.search(file_pattern, natural_language, re.IGNORECASE)
                            if file_match:
                                file_name = file_match.group(1).strip().replace('"', '').replace("'", '')
                                command = f"{base_command} {file_name}"
                                break
                        if not command:
                            command = base_command
                            
                    elif intent == 'list_files':
                        # Add appropriate flags for listing
                        if 'all' in natural_language.lower() or 'detailed' in natural_language.lower():
                            command = f"{base_command} -la"
                        elif 'long' in natural_language.lower():
                            command = f"{base_command} -l"
                        else:
                            command = base_command
                    else:
                        command = base_command
                    
                    confidence = 0.7
                    break
            
            if command:
                break
        
        # If no pattern matches, try to extract a command from the text
        if not command:
            words = natural_language.split()
            if len(words) >= 2:
                potential_command = words[0]
                if potential_command in ['ls', 'cd', 'pwd', 'mkdir', 'rm', 'cat', 'ps', 'top', 'df', 'free', 'clear', 'help']:
                    command = ' '.join(words)
                    confidence = 0.5
        
        return {
            'command': command or 'help',
            'confidence': confidence,
            'method': 'pattern',
            'original': natural_language
        }
    
    def _is_valid_command(self, command: str) -> bool:
        """Validate if the generated command is safe and valid"""
        if not command:
            return False
        
        # Check for dangerous commands
        dangerous_commands = ['rm -rf /', 'sudo', 'chmod 777', 'format', 'fdisk', 'dd if=']
        for dangerous in dangerous_commands:
            if dangerous in command.lower():
                return False
        
        # Check if it starts with a valid command
        valid_commands = ['ls', 'cd', 'pwd', 'mkdir', 'rm', 'cat', 'ps', 'top', 'df', 'free', 'clear', 'help', 'history']
        first_word = command.split()[0].lower()
        
        return first_word in valid_commands
    
    def get_suggestions(self, partial_command: str) -> List[str]:
        """Get AI-powered command suggestions based on partial input"""
        suggestions = []
        
        if not partial_command.strip():
            return ['ls', 'cd', 'pwd', 'mkdir', 'rm', 'cat', 'ps', 'top', 'help']
        
        # Basic suggestions based on partial command
        all_commands = ['ls', 'cd', 'pwd', 'mkdir', 'rm', 'cat', 'ps', 'top', 'df', 'free', 'clear', 'help', 'history']
        
        for cmd in all_commands:
            if cmd.startswith(partial_command.lower()):
                suggestions.append(cmd)
        
        # Smart suggestions based on context
        partial_lower = partial_command.lower()
        
        # File operations
        if any(word in partial_lower for word in ['list', 'show', 'files', 'directory']):
            suggestions.extend(['ls', 'ls -l', 'ls -la', 'ls -a'])
        elif any(word in partial_lower for word in ['create', 'make', 'new', 'folder', 'directory']):
            suggestions.extend(['mkdir', 'mkdir -p'])
        elif any(word in partial_lower for word in ['delete', 'remove', 'rm']):
            suggestions.extend(['rm', 'rm -r', 'rm -rf'])
        elif any(word in partial_lower for word in ['read', 'show', 'content', 'file']):
            suggestions.extend(['cat', 'cat filename'])
        elif any(word in partial_lower for word in ['go', 'change', 'navigate', 'cd']):
            suggestions.extend(['cd', 'cd directory_name'])
        elif any(word in partial_lower for word in ['process', 'running', 'ps']):
            suggestions.extend(['ps', 'ps aux', 'top'])
        elif any(word in partial_lower for word in ['system', 'info', 'status']):
            suggestions.extend(['top', 'ps', 'df', 'free'])
        elif any(word in partial_lower for word in ['disk', 'space', 'df']):
            suggestions.extend(['df', 'df -h'])
        elif any(word in partial_lower for word in ['memory', 'ram', 'free']):
            suggestions.extend(['free', 'free -h'])
        elif any(word in partial_lower for word in ['clear', 'clean']):
            suggestions.extend(['clear'])
        elif any(word in partial_lower for word in ['help', 'commands']):
            suggestions.extend(['help', 'ai-help'])
        
        # Remove duplicates and return top 5
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:5]
    
    def explain_command(self, command: str) -> str:
        """Get AI explanation of what a command does"""
        if not self.client:
            return self._basic_explanation(command)
        
        try:
            prompt = f"Explain what this terminal command does in simple terms: {command}"
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful terminal command explainer. Keep explanations simple and clear."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"AI explanation error: {e}")
            return self._basic_explanation(command)
    
    def _basic_explanation(self, command: str) -> str:
        """Basic command explanations without AI"""
        explanations = {
            'ls': 'Lists files and directories in the current location',
            'cd': 'Changes the current directory',
            'pwd': 'Shows the current directory path',
            'mkdir': 'Creates a new directory',
            'rm': 'Removes files or directories',
            'cat': 'Displays the contents of a file',
            'ps': 'Shows running processes',
            'top': 'Displays system overview and running processes',
            'df': 'Shows disk space usage',
            'free': 'Displays memory usage information',
            'clear': 'Clears the terminal screen',
            'help': 'Shows available commands',
            'history': 'Displays command history'
        }
        
        base_command = command.split()[0].lower()
        return explanations.get(base_command, f"Executes the command: {command}")

# Global AI service instance
ai_service = AICommandInterpreter()
