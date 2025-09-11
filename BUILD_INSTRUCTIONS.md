# Step-by-Step Build Instructions for Desktop Installers

This document provides detailed instructions for building cross-platform desktop installers for the Bioinformatics Chat Assistant application on macOS (Apple Silicon & Intel), Windows, and Linux.

## Prerequisites

### Required Software
- **Node.js**: Version 18.0 or higher
- **Python**: Version 3.12 or higher
- **Git**: For version control

### Platform-Specific Build Tools
- **macOS**: Xcode Command Line Tools (`xcode-select --install`)
- **Windows**: Visual Studio Build Tools or Visual Studio Community
- **Linux**: build-essential package (`sudo apt-get install build-essential`)

### Optional (for Code Signing)
- **macOS**: Apple Developer account and code signing certificate
- **Windows**: Authenticode code signing certificate from a trusted CA

## 1. Prepare the Python Backend

The Python backend must be built on each target platform to ensure compatibility.

### macOS Backend Build

1. **Create Python environment:**
   ```bash
   cd /path/to/train-a-model
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. **Build universal backend (if Python supports universal2):**
   ```bash
   pyinstaller --onefile --noconsole --target-arch universal2 \
     --hidden-import=langchain \
     --hidden-import=langchain_openai \
     --hidden-import=biopython \
     --hidden-import=uvicorn \
     --hidden-import=starlette \
     --exclude-module=tkinter \
     --exclude-module=matplotlib \
     src/drug_discovery_agent/chat_server/__main__.py
   ```

4. **Alternative: Build separate binaries for x64 and arm64:**
   ```bash
   # For x64
   pyinstaller --onefile --noconsole --target-arch x86_64 \
     --hidden-import=langchain \
     --hidden-import=langchain_openai \
     --hidden-import=biopython \
     --hidden-import=uvicorn \
     --hidden-import=starlette \
     --exclude-module=tkinter \
     --exclude-module=matplotlib \
     src/drug_discovery_agent/chat_server/__main__.py
   
   # For arm64
   pyinstaller --onefile --noconsole --target-arch arm64 \
     --hidden-import=langchain \
     --hidden-import=langchain_openai \
     --hidden-import=biopython \
     --hidden-import=uvicorn \
     --hidden-import=starlette \
     --exclude-module=tkinter \
     --exclude-module=matplotlib \
     src/drug_discovery_agent/chat_server/__main__.py
   ```

### Windows Backend Build

1. **Create Python environment:**
   ```cmd
   cd C:\path\to\train-a-model
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. **Build backend:**
   ```cmd
   pyinstaller --onefile --noconsole ^
     --hidden-import=langchain ^
     --hidden-import=langchain_openai ^
     --hidden-import=biopython ^
     --hidden-import=uvicorn ^
     --hidden-import=starlette ^
     --exclude-module=tkinter ^
     --exclude-module=matplotlib ^
     src/drug_discovery_agent/chat_server/__main__.py
   ```

### Linux Backend Build

1. **Create Python environment:**
   ```bash
   cd /path/to/train-a-model
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. **Build backend:**
   ```bash
   pyinstaller --onefile --noconsole \
     --hidden-import=langchain \
     --hidden-import=langchain_openai \
     --hidden-import=biopython \
     --hidden-import=uvicorn \
     --hidden-import=starlette \
     --exclude-module=tkinter \
     --exclude-module=matplotlib \
     src/drug_discovery_agent/chat_server/__main__.py
   ```

## 2. Build the Electron Frontend

### Setup Electron App

1. **Navigate to electron app directory:**
   ```bash
   cd electron-app
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Verify build configuration in package.json:**
   The current configuration supports:
   - macOS: DMG with universal build (x64 + arm64)
   - Windows: NSIS installer (x64 + ia32)
   - Linux: AppImage (x64)

### Platform-Specific Builds

#### macOS Build

1. **Build DMG installer:**
   ```bash
   npm run build:mac
   ```

2. **Expected output:**
   - `dist/Bioinformatics Chat Assistant-1.0.0.dmg`
   - Universal binary supporting both Intel and Apple Silicon

#### Windows Build

1. **Build NSIS installer:**
   ```bash
   npm run build:win
   ```

2. **Expected output:**
   - `dist/Bioinformatics Chat Assistant Setup 1.0.0.exe`
   - Supports both x64 and ia32 architectures

#### Linux Build

1. **Basic AppImage build:**
   ```bash
   npm run build:linux
   ```

2. **Enhanced Linux build with multiple formats:**
   
   First, update `package.json` to include deb and rpm targets:
   ```json
   "linux": {
     "target": [
       { "target": "AppImage", "arch": ["x64"] },
       { "target": "deb", "arch": ["x64"] },
       { "target": "rpm", "arch": ["x64"] }
     ],
     "category": "Science",
     "icon": "build/icon.png"
   }
   ```

   Then build:
   ```bash
   npm run build:linux
   ```

3. **Expected output:**
   - `dist/Bioinformatics Chat Assistant-1.0.0.AppImage`
   - `dist/bioinformatics-chat-assistant_1.0.0_amd64.deb` (if configured)
   - `dist/bioinformatics-chat-assistant-1.0.0.x86_64.rpm` (if configured)

### Build All Platforms

To build for all platforms at once (only works if you have the necessary tools installed):
```bash
npm run build:all
```

## 3. Code Signing (Production Builds)

Code signing is essential for production distribution to avoid security warnings.

### macOS Code Signing

1. **Set up Apple Developer account and obtain certificates**

2. **Set environment variables:**
   ```bash
   export CSC_LINK="/path/to/certificate.p12"
   export CSC_KEY_PASSWORD="your_certificate_password"
   ```

3. **Build signed DMG:**
   ```bash
   npm run build:mac
   ```

4. **Notarization (required for macOS 10.15+):**
   - electron-builder can handle notarization automatically if Apple ID credentials are provided
   - Set additional environment variables:
     ```bash
     export APPLE_ID="your_apple_id@example.com"
     export APPLE_ID_PASSWORD="app_specific_password"
     export APPLE_TEAM_ID="your_team_id"
     ```

### Windows Code Signing

1. **Obtain Authenticode certificate from a trusted CA**

2. **Set environment variables:**
   ```bash
   export WIN_CSC_LINK="/path/to/certificate.p12"
   export WIN_CSC_KEY_PASSWORD="your_certificate_password"
   ```

3. **Build signed installer:**
   ```bash
   npm run build:win
   ```

### Linux Code Signing

Linux doesn't require code signing, but you may want to GPG sign your packages for repository distribution.

## 4. Testing

### Pre-Distribution Testing

1. **Test on clean VMs:**
   - Create clean virtual machines for each target OS
   - Install the built installer/package
   - Verify the application launches and basic functionality works

2. **Test different architectures:**
   - macOS: Test on both Intel and Apple Silicon Macs
   - Windows: Test on both x64 and x86 systems (if supporting ia32)
   - Linux: Test on different distributions (Ubuntu, Fedora, etc.)

3. **Test network connectivity:**
   - Ensure the Python backend starts correctly
   - Verify API communication between frontend and backend
   - Test with actual OpenAI API calls

### Automated Testing

Add basic smoke tests to verify installer functionality:

```bash
# In electron-app directory
npm test
```

## 5. Distribution

### File Locations

After successful builds, installers will be located in:
```
electron-app/dist/
├── Bioinformatics Chat Assistant-1.0.0.dmg          # macOS
├── Bioinformatics Chat Assistant Setup 1.0.0.exe    # Windows
├── Bioinformatics Chat Assistant-1.0.0.AppImage     # Linux AppImage
├── bioinformatics-chat-assistant_1.0.0_amd64.deb    # Linux Debian
└── bioinformatics-chat-assistant-1.0.0.x86_64.rpm   # Linux RPM
```

### Distribution Channels

- **Direct Download:** Host installers on your website or file hosting service
- **GitHub Releases:** Upload installers as release assets
- **Package Managers:**
  - macOS: Submit to Mac App Store or use Homebrew Cask
  - Windows: Submit to Microsoft Store or use Chocolatey
  - Linux: Submit to distribution repositories or use Snap Store

## 6. Troubleshooting

### Common Issues

1. **Python Backend Not Found:**
   - Ensure PyInstaller built the backend successfully
   - Check that the backend executable is included in electron-builder's `extraResources`

2. **Code Signing Failures:**
   - Verify certificate validity and password
   - Ensure proper environment variables are set
   - Check that certificate supports the target platform

3. **Build Failures on Specific Platforms:**
   - Ensure all required build tools are installed
   - Check that Node.js and Python versions meet requirements
   - Review build logs for specific error messages

4. **Runtime Errors:**
   - Check that all Python dependencies are properly bundled
   - Verify that environment variables are correctly set in the packaged app
   - Test with verbose logging enabled

### Debug Builds

For debugging purposes, you can create debug builds with additional logging:

```bash
# Enable debug mode
export DEBUG=electron-builder

# Build with additional logging
npm run build:mac -- --publish=never
```

## 7. Maintenance

### Updating Dependencies

1. **Update Python dependencies:**
   ```bash
   pip install -r requirements.txt --upgrade
   pip freeze > requirements.txt
   ```

2. **Update Node.js dependencies:**
   ```bash
   cd electron-app
   npm update
   npm audit fix
   ```

3. **Update Electron:**
   ```bash
   cd electron-app
   npm install electron@latest --save-dev
   ```

### Version Management

Update version numbers in:
- `package.json` (root and electron-app)
- `pyproject.toml`
- `electron-app/package.json`

This ensures consistent versioning across all build artifacts.