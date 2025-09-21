// Terminal JavaScript functionality
class Terminal {
    constructor() {
        this.socket = io();
        this.commandHistory = [];
        this.historyIndex = -1;
        this.currentCommand = '';
        this.isHistoryMode = false;
        
        this.initializeElements();
        this.setupEventListeners();
        this.setupSocketListeners();
        this.startSystemInfoUpdates();
    }
    
    initializeElements() {
        this.terminalInput = document.getElementById('terminal-input');
        this.terminalOutput = document.getElementById('terminal-output');
        this.cursor = document.getElementById('cursor');
        this.historyPanel = document.getElementById('history-panel');
        this.historyContent = document.getElementById('history-content');
        this.helpModal = document.getElementById('help-modal');
        
        // System info elements
        this.cpuInfo = document.getElementById('cpu-info');
        this.memoryInfo = document.getElementById('memory-info');
        this.diskInfo = document.getElementById('disk-info');
    }
    
    setupEventListeners() {
        // Terminal input handling
        this.terminalInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.terminalInput.addEventListener('input', (e) => this.handleInput(e));
        
        // Focus management
        this.terminalInput.addEventListener('focus', () => this.showCursor());
        this.terminalInput.addEventListener('blur', () => this.hideCursor());
        
        // Global shortcuts
        document.addEventListener('keydown', (e) => this.handleGlobalShortcuts(e));
        
        // Modal close handlers
        document.querySelector('.close-modal').addEventListener('click', () => this.closeHelp());
        document.querySelector('.close-history').addEventListener('click', () => this.toggleHistory());
        
        // Click outside modal to close
        this.helpModal.addEventListener('click', (e) => {
            if (e.target === this.helpModal) {
                this.closeHelp();
            }
        });
        
        // Auto-focus input
        this.terminalInput.focus();
    }
    
    setupSocketListeners() {
        this.socket.on('connect', () => {
            this.addOutput('Connected to terminal server', 'success');
        });
        
        this.socket.on('disconnect', () => {
            this.addOutput('Disconnected from terminal server', 'error');
        });
        
        this.socket.on('terminal_output', (data) => {
            this.handleTerminalOutput(data);
        });
        
        this.socket.on('command_history', (data) => {
            this.commandHistory = data.history || [];
            this.updateHistoryPanel();
        });
        
        this.socket.on('system_info', (data) => {
            this.updateSystemInfo(data);
        });
        
        this.socket.on('ai_suggestions', (data) => {
            this.showAISuggestions(data.suggestions);
        });
        
        this.socket.on('ai_interpretation', (data) => {
            this.showAIInterpretation(data);
        });
        
        this.socket.on('command_explanation', (data) => {
            this.showCommandExplanation(data);
        });
    }
    
    handleKeyDown(e) {
        switch(e.key) {
            case 'Enter':
                e.preventDefault();
                this.executeCommand();
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.navigateHistory(-1);
                break;
                
            case 'ArrowDown':
                e.preventDefault();
                this.navigateHistory(1);
                break;
                
            case 'Tab':
                e.preventDefault();
                this.handleTabCompletion();
                break;
                
            case 'Escape':
                e.preventDefault();
                this.clearInput();
                break;
        }
    }
    
    handleInput(e) {
        this.currentCommand = e.target.value;
        this.isHistoryMode = false;
        
        // Get AI suggestions as user types
        if (this.currentCommand.length > 2) {
            this.socket.emit('get_ai_suggestions', { command: this.currentCommand });
        }
    }
    
    handleGlobalShortcuts(e) {
        if (e.ctrlKey) {
            switch(e.key) {
                case 'l':
                    e.preventDefault();
                    this.clearTerminal();
                    break;
                case 'h':
                    e.preventDefault();
                    this.toggleHistory();
                    break;
            }
        }
    }
    
    executeCommand() {
        const command = this.terminalInput.value.trim();
        
        if (!command) {
            this.addPromptLine();
            return;
        }
        
        // Add command to history
        this.commandHistory.push(command);
        this.historyIndex = this.commandHistory.length;
        
        // Display the command
        this.addCommandLine(command);
        
        // Send to server
        this.socket.emit('command', { command: command });
        
        // Clear input
        this.terminalInput.value = '';
        this.currentCommand = '';
    }
    
    addCommandLine(command) {
        const line = document.createElement('div');
        line.className = 'output-line command-highlight';
        line.innerHTML = `<span class="prompt">user@terminal:~$</span> ${this.escapeHtml(command)}`;
        this.terminalOutput.appendChild(line);
        this.scrollToBottom();
    }
    
    addPromptLine() {
        const line = document.createElement('div');
        line.className = 'output-line';
        line.innerHTML = '<span class="prompt">user@terminal:~$</span>';
        this.terminalOutput.appendChild(line);
        this.scrollToBottom();
    }
    
    handleTerminalOutput(data) {
        if (data.type === 'clear') {
            this.clearTerminal();
            return;
        }
        
        if (data.type === 'welcome') {
            this.addOutput(data.output, 'info');
            return;
        }
        
        if (data.type === 'ai_interpretation') {
            // Show AI interpretation and execute the interpreted command
            this.addOutput(data.output, 'info');
            
            // Add a button to execute the interpreted command
            const buttonDiv = document.createElement('div');
            buttonDiv.className = 'ai-execution-prompt';
            buttonDiv.innerHTML = `
                <span class="ai-prompt-text">Execute: <code>${data.interpreted_command}</code></span>
                <button class="ai-execute-btn" onclick="terminal.executeInterpretedCommand('${data.interpreted_command}')">Execute</button>
                <button class="ai-cancel-btn" onclick="terminal.cancelAIExecution()">Cancel</button>
            `;
            this.terminalOutput.appendChild(buttonDiv);
            this.scrollToBottom();
            return;
        }
        
        if (data.output) {
            const outputClass = data.type === 'error' ? 'error' : 
                              data.type === 'success' ? 'success' : 'output';
            this.addOutput(data.output, outputClass);
        }
        
        // Add new prompt line
        this.addPromptLine();
    }
    
    executeInterpretedCommand(command) {
        // Remove the AI execution prompt
        const promptDiv = document.querySelector('.ai-execution-prompt');
        if (promptDiv) {
            promptDiv.remove();
        }
        
        // Execute the interpreted command
        this.socket.emit('command', { command: command });
    }
    
    cancelAIExecution() {
        // Remove the AI execution prompt
        const promptDiv = document.querySelector('.ai-execution-prompt');
        if (promptDiv) {
            promptDiv.remove();
        }
        
        // Add new prompt line
        this.addPromptLine();
    }
    
    addOutput(text, className = '') {
        const lines = text.split('\n');
        lines.forEach(line => {
            const outputLine = document.createElement('div');
            outputLine.className = `output-line ${className}`;
            outputLine.textContent = line;
            this.terminalOutput.appendChild(outputLine);
        });
        this.scrollToBottom();
    }
    
    navigateHistory(direction) {
        if (this.commandHistory.length === 0) return;
        
        if (!this.isHistoryMode) {
            this.isHistoryMode = true;
            this.historyIndex = this.commandHistory.length;
        }
        
        this.historyIndex += direction;
        
        if (this.historyIndex < 0) {
            this.historyIndex = 0;
        } else if (this.historyIndex >= this.commandHistory.length) {
            this.historyIndex = this.commandHistory.length;
            this.terminalInput.value = this.currentCommand;
            return;
        }
        
        this.terminalInput.value = this.commandHistory[this.historyIndex] || '';
    }
    
    handleTabCompletion() {
        // Basic tab completion - can be enhanced
        const command = this.terminalInput.value;
        const commonCommands = ['ls', 'cd', 'pwd', 'mkdir', 'rm', 'cat', 'ps', 'top', 'df', 'free', 'clear', 'history', 'help'];
        
        const matches = commonCommands.filter(cmd => cmd.startsWith(command));
        
        if (matches.length === 1) {
            this.terminalInput.value = matches[0] + ' ';
        } else if (matches.length > 1) {
            this.addOutput(`Available commands: ${matches.join(', ')}`, 'info');
        }
    }
    
    clearInput() {
        this.terminalInput.value = '';
        this.currentCommand = '';
        this.isHistoryMode = false;
    }
    
    clearTerminal() {
        this.terminalOutput.innerHTML = '';
        this.addPromptLine();
    }
    
    scrollToBottom() {
        this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
    }
    
    showCursor() {
        this.cursor.style.display = 'inline-block';
    }
    
    hideCursor() {
        this.cursor.style.display = 'none';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // History panel methods
    toggleHistory() {
        this.historyPanel.classList.toggle('open');
        if (this.historyPanel.classList.contains('open')) {
            this.socket.emit('get_history');
        }
    }
    
    updateHistoryPanel() {
        this.historyContent.innerHTML = '';
        
        if (this.commandHistory.length === 0) {
            this.historyContent.innerHTML = '<div class="history-item">No commands in history</div>';
            return;
        }
        
        this.commandHistory.forEach((command, index) => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            historyItem.innerHTML = `<span style="color: #666;">${index + 1}:</span> ${this.escapeHtml(command)}`;
            historyItem.addEventListener('click', () => {
                this.terminalInput.value = command;
                this.terminalInput.focus();
                this.toggleHistory();
            });
            this.historyContent.appendChild(historyItem);
        });
    }
    
    // Help modal methods
    showHelp() {
        this.helpModal.style.display = 'block';
    }
    
    closeHelp() {
        this.helpModal.style.display = 'none';
    }
    
    // System info updates
    startSystemInfoUpdates() {
        // Update system info every 2 seconds
        setInterval(() => {
            this.socket.emit('get_system_info');
        }, 2000);
    }
    
    updateSystemInfo(data) {
        if (data.error) {
            console.error('System info error:', data.error);
            return;
        }
        
        this.cpuInfo.textContent = `CPU: ${data.cpu_percent.toFixed(1)}%`;
        this.memoryInfo.textContent = `RAM: ${data.memory_percent.toFixed(1)}%`;
        this.diskInfo.textContent = `Disk: ${data.disk_percent.toFixed(1)}%`;
    }
    
    showAISuggestions(suggestions) {
        // Remove existing suggestions
        const existingSuggestions = document.querySelector('.ai-suggestions');
        if (existingSuggestions) {
            existingSuggestions.remove();
        }
        
        if (suggestions && suggestions.length > 0) {
            const suggestionDiv = document.createElement('div');
            suggestionDiv.className = 'ai-suggestions';
            suggestionDiv.innerHTML = `
                <div class="suggestion-header">🤖 AI Suggestions:</div>
                <div class="suggestion-list">
                    ${suggestions.map(suggestion => 
                        `<div class="suggestion-item" onclick="terminal.useSuggestion('${suggestion}')">${suggestion}</div>`
                    ).join('')}
                </div>
            `;
            
            this.terminalOutput.appendChild(suggestionDiv);
            this.scrollToBottom();
        }
    }
    
    useSuggestion(suggestion) {
        this.terminalInput.value = suggestion;
        this.terminalInput.focus();
        
        // Remove suggestions
        const existingSuggestions = document.querySelector('.ai-suggestions');
        if (existingSuggestions) {
            existingSuggestions.remove();
        }
    }
    
    showAIInterpretation(data) {
        if (data.confidence > 0.5) {
            this.addOutput(`🤖 AI interpreted: "${data.original}" → "${data.command}"`, 'info');
        }
    }
    
    showCommandExplanation(data) {
        this.addOutput(`💡 ${data.command}: ${data.explanation}`, 'info');
    }
}

// Global functions for HTML onclick handlers
function toggleHistory() {
    terminal.toggleHistory();
}

function closeHelp() {
    terminal.closeHelp();
}

// Initialize terminal when page loads
let terminal;
document.addEventListener('DOMContentLoaded', () => {
    terminal = new Terminal();
    
    // Handle help command
    terminal.socket.on('terminal_output', (data) => {
        if (data.output && data.output.includes('help')) {
            terminal.showHelp();
        }
    });
});

// Handle window resize
window.addEventListener('resize', () => {
    if (terminal) {
        terminal.scrollToBottom();
    }
});

// Handle page visibility change
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && terminal) {
        terminal.terminalInput.focus();
    }
});
