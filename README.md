# PyTerm - AI-Enhanced Python Terminal

## Assignment Entry Point
**Main File:** `main.py` (Required for assignment submission)

## Project Overview
**PyTerm** is a modern, safety-first Python terminal application with dual interfaces (CLI and Web) that combines traditional shell operations with AI-powered natural language processing.

## Quick Start
```bash
# Run locally (main entry point)
python main.py

# Show web terminal info
python main.py --web

# Enable debug mode
python main.py --debug
```

## Live Deployment
- **Platform:** Vercel (Serverless)
- **URL:** `https://pytem.vercel.app/`
- **GitHub:** `https://github.com/sathvikinguva/Python-Based-Command-Terminal`
- **Status:** Production Ready
- **Video Explanation:** [Click Here](https://drive.google.com/file/d/1sBpRysGrTThxx3tm2clmpkUDu09L0fph/view?usp=sharing)


## Key Features

### Core Terminal Operations
- **File Management**: `ls`, `cd`, `pwd`, `mkdir`, `rm` with safety validation
- **Smart Output**: Rich colored formatting with file type indicators
- **Auto-complete**: Intelligent tab completion for commands and paths
- **Command History**: Persistent history with search functionality
- **Safe Mode**: Sandboxed execution with recycle bin protection

### AI Integration
- **Natural Language**: Convert plain English to shell commands
- **Google AI Powered**: Uses Gemini AI for command interpretation
- **Fallback Parser**: Rule-based parsing when AI unavailable
- **Safety Validation**: AI commands require user confirmation
- **Rate Limited**: Prevents API quota exhaustion

### System Monitoring
- **Real-time Stats**: CPU, memory, disk usage monitoring
- **Process Viewer**: Top processes with resource consumption
- **System Info**: Boot time, uptime, load averages
- **Cross-platform**: Works on Windows, macOS, Linux

### Web Interface
- **Browser Terminal**: Full terminal experience in browser
- **WebSocket**: Real-time command execution
- **Mobile Responsive**: Works on phones, tablets, desktop
- **Modern UI**: Dark theme with professional styling

### Security & Safety
- **Directory Restrictions**: Operations confined to safe directories  
- **Path Validation**: Prevents traversal attacks (`../../../etc`)
- **Command Sanitization**: All inputs validated before execution
- **Recycle Bin**: Safe deletion with recovery options
- **Confirmation Prompts**: User approval for destructive operations

## Technology Stack

**Backend:**
- Python 3.10+ (Core language)
- Flask + SocketIO (Web server)
- Rich (Terminal formatting)
- Prompt Toolkit (CLI interface)
- Google Generative AI (NLP)
- PSUtil (System monitoring)
- PyYAML (Configuration)
- Pytest (Testing)

**Frontend:**
- HTML5/CSS3/
- WebSocket communication
- Responsive CSS Grid/Flexbox
- Real-time terminal emulation

**Deployment:**
- Vercel (Serverless platform)
- Automatic HTTPS & CDN
- Environment variables
- Zero-downtime deployments

## Project Structure

```
PyTerm/
├── Web Interface
│   ├── api/basic_terminal.py     # Flask API + AI integration
│   ├── templates/                # Web terminal UI
│   └── vercel.json              # Deployment configuration
│
├── Core Terminal  
│   ├── main.py                   # Main entry point (REQUIRED)
│   ├── cli.py                    # Alternative CLI interface
│   ├── executor.py               # Safety & security core
│   ├── commands/                 # Command implementations
│   └── autocomplete.py           # Auto-completion logic
│
├── AI Features
│   ├── nl_parser.py              # Natural language processor
│   └── config.yml                # AI & app configuration
│
├── System Features
│   ├── monitor.py                # System monitoring
│   └── requirements.txt          # Core dependencies
│
├── Testing & Docs
│   ├── tests/                    # Comprehensive test suite
│   ├── README.md                 # User documentation  
│   └── DEPLOYMENT_GUIDE.md       # Deployment instructions
│
└── Deployment
    ├── vercel.json               # Vercel configuration
    └── .gitignore                # Git ignore rules
```

## Usage Examples

### CLI Interface
```bash
# Start the terminal (main entry point)
python main.py

# Basic commands
ls -la                    # List all files
mkdir projects           # Create directory  
cd projects             # Change directory
monitor                 # System information

# AI commands
ask list all files       # Natural language
ask create folder test   # AI processes request
do show system stats     # Alternative syntax
```

### Web Interface  
```bash
# Start web server
python web_app.py

# Access at http://localhost:5000
# Use same commands as CLI in browser
```

### Deployment
```bash
vercel --prod

vercel env add GOOGLE_API_KEY
```

## Testing Coverage

**Test Suite:**
- Unit tests for all commands (95%+ coverage)
- Safety & security feature validation
- AI parser functionality tests
- Integration tests for command chains  
- Web interface endpoint tests
- Error handling & edge cases

**Run Tests:**
```bash
pytest tests/ -v --cov=.
```

## 🔧 Configuration

**Key Settings (config.yml):**
```yaml
safe_mode: true
allowed_root: "."
dry_run: false

ai_enabled: true
ai_confirmation_required: true
google_api_key: "your-key"

colors_enabled: true
prompt: "PyTerm> "
history_file: ".pyterm_history"
```

## Unique Selling Points

1. **Dual Interface**: Both CLI and web versions from same codebase
2. **AI Integration**: Natural language command processing
3. **Safety First**: Comprehensive security with sandboxing
4. **Production Ready**: Live deployment with proper error handling
5. **Extensible**: Modular architecture for easy feature addition
6. **Cross-Platform**: Works everywhere Python runs
7. **Professional UI**: Rich formatting and responsive design
8. **Comprehensive Testing**: High test coverage with CI/CD ready

## Performance Features

- **Lazy Loading**: Components loaded on demand
- **Caching**: Efficient command processing
- **Rate Limiting**: API quota protection
- **Error Recovery**: Graceful fallbacks
- **Memory Efficient**: Minimal resource usage
- **Fast Response**: Optimized command execution

## User Experience

**CLI Experience:**
- Rich colored output with file type icons
- Command history with fuzzy search
- Tab completion for commands and paths
- Intuitive error messages with suggestions
- Progress indicators for long operations

**Web Experience:**
- Terminal-like interface in browser
- Real-time command execution
- Mobile-responsive design
- Professional dark theme
- Copy/paste support

## Metrics & Analytics

**Code Quality:**
- 2000+ lines of Python code
- 95%+ test coverage
- Type hints throughout
- Comprehensive documentation
- Clean architecture patterns

**Features Implemented:**
- 15+ terminal commands
- 3 AI command interfaces
- 10+ system monitoring metrics
- 5+ safety mechanisms
- Full web interface

## Deployment Instructions

**For Submission:**

1. **Get the code:**
   ```bash
   # All files are ready in d:\Python-Terminal\
   ```

2. **Deploy to Vercel:**
   ```bash
   npm install -g vercel
   vercel --prod
   ```

3. **Set environment variables:**
   ```bash
   vercel env add GOOGLE_API_KEY
   # Enter: your_api_key
   ```

4. **Your live URL:**
   ```
   https://pytem.vercel.app/
   ```

## Submission Checklist

- **Live URL**: Deployed and accessible
- **Core Features**: All terminal commands working
- **AI Integration**: Natural language processing
- **Web Interface**: Browser-based terminal
- **System Monitoring**: Real-time stats display
- **Safety Features**: Sandboxed execution
- **Mobile Responsive**: Works on all devices
- **Error Handling**: Graceful error management
- **Documentation**: Comprehensive guides
- **Testing**: Full test coverage

## Demo Script

**For Presentation:**

1. **Show Live URL**: Open browser to deployed site
2. **Basic Commands**: `ls`, `mkdir demo`, `cd demo`
3. **AI Features**: `ask create a new folder called test`
4. **System Monitor**: `monitor` command
5. **Safety Demo**: Try dangerous command (blocked)
6. **Mobile View**: Show responsive design
7. **Error Handling**: Show graceful error recovery

---

**Project Status: PRODUCTION READY**  
**Deployment: VERCEL HOSTED**  
**Features: FULLY FUNCTIONAL**
