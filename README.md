# Python Terminal Web Application

A fully functional web-based terminal that mimics the behavior of a real system terminal, built with Python Flask backend and responsive web frontend.

## Features

### Core Terminal Commands
- **File Operations**: `ls`, `cd`, `pwd`, `mkdir`, `rm`, `cat`
- **System Monitoring**: `ps`, `top`, `df`, `free`
- **Terminal Features**: `clear`, `history`, `help`

### Advanced Features
- **Real-time Communication**: WebSocket-based communication for instant responses
- **Command History**: Navigate through previous commands with arrow keys
- **Auto-completion**: Tab completion for common commands
- **System Monitoring**: Real-time CPU, memory, and disk usage display
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Modern UI**: Terminal-like interface with smooth animations

### AI Features ✨
- **Natural Language Commands**: Type in plain English and AI converts to terminal commands
- **Smart Parameter Extraction**: AI automatically extracts file names, directory names, and parameters
- **Command Suggestions**: Get intelligent suggestions as you type
- **Command Explanation**: AI explains what commands do
- **Interactive Execution**: Review AI interpretations before executing

### Optional Enhancements (Future)
- Advanced command history search
- Custom themes and color schemes
- File upload/download capabilities
- Multi-user support
- Voice command support

## Installation

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd terminal
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Open your browser**
   Navigate to `http://localhost:5000`

## Usage

### Basic Commands
- `ls` - List directory contents
- `ls -l` - List with detailed information
- `cd <directory>` - Change directory
- `pwd` - Print working directory
- `mkdir <name>` - Create directory
- `rm <file>` - Remove file
- `rm -r <directory>` - Remove directory recursively
- `cat <file>` - Display file contents

### System Monitoring
- `ps` - Show running processes
- `top` - System overview
- `df` - Disk usage information
- `free` - Memory usage information

### Terminal Features
- `clear` - Clear terminal screen
- `history` - Show command history
- `help` - Show help modal
- `ai-help` - Show AI features help

### AI Natural Language Examples
- "create a folder called my project" → `mkdir my_project`
- "list all files in detail" → `ls -la`
- "go to the documents folder" → `cd documents`
- "delete the test folder" → `rm -r test`
- "show me what's in file.txt" → `cat file.txt`
- "what processes are running?" → `ps`
- "show system information" → `top`

### Keyboard Shortcuts
- `↑` / `↓` - Navigate command history
- `Tab` - Auto-complete commands
- `Ctrl + L` - Clear screen
- `Ctrl + H` - Show history panel
- `Escape` - Clear current input

## Project Structure

```
terminal/
├── app.py                 # Flask backend with terminal logic
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── index.html        # Main HTML template
└── static/
    ├── style.css         # CSS styling
    └── script.js         # Frontend JavaScript
```

## Technical Details

### Backend (Python)
- **Flask**: Web framework for handling HTTP requests
- **Flask-SocketIO**: WebSocket communication for real-time updates
- **psutil**: System and process monitoring
- **subprocess**: Command execution
- **os**: File system operations

### Frontend (Web)
- **HTML5**: Semantic markup
- **CSS3**: Responsive design with animations
- **JavaScript**: Interactive functionality
- **Socket.IO**: Real-time communication
- **Font Awesome**: Icons

### Security Considerations
- Commands are executed with appropriate timeouts
- Input validation and sanitization
- Error handling for invalid commands
- Safe file operations with proper path handling

## Browser Compatibility

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Development

To run in development mode:
```bash
export FLASK_ENV=development
python app.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Troubleshooting

### Common Issues

1. **Port already in use**
   - Change the port in `app.py` (line with `socketio.run`)
   - Or kill the process using port 5000

2. **Permission denied errors**
   - Some commands may require elevated permissions
   - The terminal runs with the same permissions as the Python process

3. **Commands not working**
   - Check if the command exists on your system
   - Some commands may be platform-specific

4. **WebSocket connection issues**
   - Ensure your browser supports WebSockets
   - Check firewall settings

### Performance Tips

- The terminal is optimized for moderate usage
- For heavy command execution, consider implementing command queuing
- System monitoring updates every 2 seconds to balance performance and responsiveness
