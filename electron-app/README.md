# Bioinformatics Chat Assistant - Desktop App

## 📋 Prerequisites

### Development Environment

- **Node.js**: Version 18.0 or higher
- **Python**: Version 3.12 or higher
- **Git**: For version control
- **Platform-specific build tools**:
    - Windows: Visual Studio Build Tools
    - macOS: Xcode Command Line Tools
    - Linux: build-essential package

### API Configuration

- **OpenAI API Key**: Required for AI functionality
- Create `.env` file in project root with: `OPENAI_API_KEY=your_key_here`

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd deda-drug-evaluation-and-discovery-agent
```

### 2. Backend Setup

```bash
# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
# Navigate to Electron app
cd electron-app

# Install Node.js dependencies
npm install
```

### 4. Development Mode

```bash
# From electron-app directory
npm run dev
```

This starts both the Python backend server and Electron frontend simultaneously.

## 🔌 Backend Integration

### API Endpoints

The Electron app communicates with a Python backend server running on `localhost:8080`:

### Session Flow

1. **App Startup**:
    - Electron launches Python backend server
    - Frontend creates new session via `POST /sessions`
    - Session ID stored for all subsequent requests

2. **Chat Interaction**:
    - User types message and clicks send
    - Frontend sends to `POST /api/chat` with session_id
    - Backend maintains conversation context automatically
    - AI response displayed in chat interface

3. **App Shutdown**:
    - Session cleanup via `DELETE /sessions/{id}`
    - Python backend server terminated gracefully

## 🛠️ Development Guide

### Available Scripts

```bash
# Development (runs both backend and frontend)
npm run dev

# Start only Python backend server
npm run dev:python

# Start only Electron frontend 
npm run dev:electron

# Production build
npm run build

# Create platform installers
npm run package

# Run tests
npm test
```

### Development Workflow

1. **Code Changes**: Edit files in `src/` directory
2. **Hot Reload**: Electron automatically reloads on changes
3. **Backend Restart**: Manual restart needed for Python changes
4. **DevTools**: Press F12 or Ctrl+Shift+I for debugging
5. **Logging**: Check terminal for backend logs, DevTools console for frontend

### Debugging

#### Frontend Debugging

- **DevTools**: Full Chrome DevTools available
- **Console Logging**: Use `console.log()` in renderer.js
- **Network Tab**: Monitor HTTP requests to backend
- **Sources Tab**: Set breakpoints in JavaScript code

#### Backend Debugging

- **Terminal Output**: Python server logs appear in terminal
- **Health Endpoint**: Check `localhost:8080/health` in browser
- **Session Status**: Monitor active sessions in health response
- **Verbose Mode**: Use `npm run dev:python -- --verbose` for detailed logs

## 🏭 Build & Packaging

### Development Build

```bash
npm run build
```

### Platform-Specific Builds

```bash
# Windows installer
npm run build:win

# macOS DMG
npm run build:mac  

# Linux AppImage
npm run build:linux

# All platforms
npm run build:all
```

## 🔧 Configuration

### Environment Variables

```bash
# .env file in project root
OPENAI_API_KEY=your_openai_api_key_here
CHAT_SERVER_PORT=8080
ELECTRON_DEV_MODE=true
```

### Application Settings

Settings are stored in platform-specific locations:

- **Windows**: `%APPDATA%/bioinformatics-chat`
- **macOS**: `~/Library/Preferences/bioinformatics-chat`
- **Linux**: `~/.config/bioinformatics-chat`

### Customization

- **UI Themes**: Modify `src/styles.css`
- **Backend Port**: Change in `main.js` and backend startup
- **Window Size**: Configure in `main.js` window options
- **Menu Items**: Customize in `main.js` menu template

## 📦 Creating Distribution Installers

### Prerequisites for Building Installers

Before creating installers, ensure you have:

1. **Python Backend Built**: The Python backend must be built first using PyInstaller
2. **Environment Configuration**: `.env` file with required API keys
3. **Platform-Specific Tools**: Native build tools for your target platform

### Step 1: Build Python Backend

From the electron-app directory:

```bash
# Build the Python backend executable using the npm script
npm run build:python
```

This runs PyInstaller with the correct configuration and creates:

- `../dist/__main__` - The Python backend executable (in the project root dist folder)
- `../dist/__main__.app` - macOS app bundle (on macOS)

**Note**: The npm script automatically handles:

- Detecting the correct target architecture automatically
- Including necessary hidden imports (Bio, langchain, uvicorn, etc.)
- Excluding unnecessary modules (tkinter, matplotlib)
- Using appropriate PyInstaller flags (--onefile, --noconsole)

### Step 2: Build Electron Installers

Navigate to the electron-app directory and install dependencies:

```bash
cd electron-app
npm install
```

#### Build for Current Platform

```bash
# Build DMG installer for macOS (current architecture)
npm run build:mac

# Build installer for Windows
npm run build:win

# Build AppImage for Linux
npm run build:linux
```

#### Build for Specific Architectures

```bash
# Build for Intel Macs (x64)
npm run build:mac:x64

# Build for Apple Silicon Macs (arm64)  
npm run build:mac:arm64

# Build for both architectures
npm run build:mac:universal

# Build for apple store
# Put macappdistribution.provisionprofile file in the electron-app folder for signing
npm run build:mas:x64
npm run build:mas:arm64
```

#### Build for All Platforms

```bash
# Create installers for all supported platforms
npm run build:all
```

### Output Files

Installers are created in `electron-app/dist/`:

- **macOS**: `Bioinformatics Chat Assistant-1.0.0.dmg` (or with architecture suffix)
- **Windows**: `Bioinformatics Chat Assistant Setup 1.0.0.exe`
- **Linux**: `Bioinformatics Chat Assistant-1.0.0.AppImage`

### Important Notes

#### Environment Variables

The `.env` file containing your OpenAI API key is automatically included in the installer build process. The application
uses enhanced path resolution to find environment variables in these locations:

1. **Development**: `.env` file in project root
2. **Production**: Bundled within the application package at `Contents/Resources/.env`
3. **Automatic Detection**: The app searches multiple paths to ensure reliable environment loading

#### Troubleshooting

**Environment Variable Issues:**

- If you see "api_key client option must be set" errors, ensure your `.env` file contains `OPENAI_API_KEY=your_key_here`
- The app includes debug logging that shows which `.env` file was loaded (check console output)
- For production apps, the environment file is bundled automatically during the build process

**Import Errors:**

- If you encounter relative import errors, ensure you're using the latest build with fixed absolute imports
- The `npm run build:python` command now handles import resolution automatically

