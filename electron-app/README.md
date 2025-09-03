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
cd train-a-model
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
   - Frontend creates new session via `POST /api/sessions`
   - Session ID stored for all subsequent requests

2. **Chat Interaction**:
   - User types message and clicks send
   - Frontend sends to `POST /api/chat` with session_id
   - Backend maintains conversation context automatically
   - AI response displayed in chat interface

3. **App Shutdown**:
   - Session cleanup via `DELETE /api/sessions/{id}`
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
