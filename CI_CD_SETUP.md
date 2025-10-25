# CI/CD Setup Plan for Cross-Platform Desktop Installers

This document outlines a comprehensive CI/CD setup for automatically building cross-platform desktop installers for the Bioinformatics Chat Assistant using GitHub Actions.

## Overview

### Objectives
- Automate building for macOS (Apple Silicon & Intel), Windows, and Linux
- Support code signing for production releases
- Generate multiple Linux package formats (AppImage, deb, rpm)
- Provide artifact storage and release management
- Ensure consistent builds across all platforms

### CI/CD Strategy
- **Platform**: GitHub Actions (supports native macOS, Windows, and Linux runners)
- **Triggers**: Push to main branch, pull requests, and git tags
- **Parallelization**: Build all platforms simultaneously for faster CI/CD
- **Artifacts**: Store build outputs and make them available for download/release

## 1. Repository Secrets Configuration

### Required Secrets

Add the following secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

#### Code Signing Secrets
```
# macOS Code Signing
CSC_LINK                    # Base64 encoded .p12 certificate or file path
CSC_KEY_PASSWORD           # Certificate password
APPLE_ID                   # Apple ID for notarization (optional)
APPLE_ID_PASSWORD          # App-specific password for Apple ID
APPLE_TEAM_ID             # Apple Developer Team ID

# Windows Code Signing
WIN_CSC_LINK              # Base64 encoded .p12/.pfx certificate
WIN_CSC_KEY_PASSWORD      # Certificate password

# API Keys
OPENAI_API_KEY            # OpenAI API key for testing (optional)
```

#### Certificate Preparation

**For macOS:**
```bash
# Export certificate from Keychain as .p12
# Then encode to base64
base64 -i certificate.p12 -o certificate_base64.txt
# Copy contents of certificate_base64.txt to CSC_LINK secret
```

**For Windows:**
```bash
# If you have a .pfx file
base64 certificate.pfx > certificate_base64.txt
# Copy contents to WIN_CSC_LINK secret
```

## 2. GitHub Actions Workflow

### Main Workflow File

Create `.github/workflows/build-desktop-apps.yml`:

```yaml
name: Build Desktop Applications

on:
  push:
    branches: [ main, develop ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main ]

env:
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.12'

jobs:
  # Job 1: Build for macOS
  build-macos:
    runs-on: macos-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ env.NODE_VERSION }}
        cache: 'npm'
        cache-dependency-path: electron-app/package-lock.json
        
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        
    - name: Cache Python dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
          
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller
        
    - name: Create .env file
      run: |
        echo "OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}" > .env
        
    - name: Build Python backend (universal2)
      run: |
        pyinstaller --onefile --noconsole --target-arch universal2 \
          --hidden-import=langchain \
          --hidden-import=langchain_openai \
          --hidden-import=biopython \
          --hidden-import=uvicorn \
          --hidden-import=starlette \
          --exclude-module=tkinter \
          --exclude-module=matplotlib \
          --distpath=dist \
          src/drug_discovery_agent/chat_server/__main__.py
          
    - name: Install Node.js dependencies
      working-directory: electron-app
      run: npm ci
      
    - name: Build Electron app for macOS
      working-directory: electron-app
      env:
        CSC_LINK: ${{ secrets.CSC_LINK }}
        CSC_KEY_PASSWORD: ${{ secrets.CSC_KEY_PASSWORD }}
        APPLE_ID: ${{ secrets.APPLE_ID }}
        APPLE_ID_PASSWORD: ${{ secrets.APPLE_ID_PASSWORD }}
        APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
      run: npm run build:mac
      
    - name: Upload macOS artifacts
      uses: actions/upload-artifact@v3
      with:
        name: macos-installer
        path: electron-app/dist/*.dmg
        retention-days: 30

  # Job 2: Build for Windows
  build-windows:
    runs-on: windows-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ env.NODE_VERSION }}
        cache: 'npm'
        cache-dependency-path: electron-app/package-lock.json
        
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        
    - name: Cache Python dependencies
      uses: actions/cache@v3
      with:
        path: ~\AppData\Local\pip\Cache
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
          
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller
        
    - name: Create .env file
      run: |
        echo "OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}" > .env
        
    - name: Build Python backend
      run: |
        pyinstaller --onefile --noconsole `
          --hidden-import=langchain `
          --hidden-import=langchain_openai `
          --hidden-import=biopython `
          --hidden-import=uvicorn `
          --hidden-import=starlette `
          --exclude-module=tkinter `
          --exclude-module=matplotlib `
          --distpath=dist `
          src/drug_discovery_agent/chat_server/__main__.py
          
    - name: Install Node.js dependencies
      working-directory: electron-app
      run: npm ci
      
    - name: Build Electron app for Windows
      working-directory: electron-app
      env:
        WIN_CSC_LINK: ${{ secrets.WIN_CSC_LINK }}
        WIN_CSC_KEY_PASSWORD: ${{ secrets.WIN_CSC_KEY_PASSWORD }}
      run: npm run build:win
      
    - name: Upload Windows artifacts
      uses: actions/upload-artifact@v3
      with:
        name: windows-installer
        path: electron-app/dist/*.exe
        retention-days: 30

  # Job 3: Build for Linux
  build-linux:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ env.NODE_VERSION }}
        cache: 'npm'
        cache-dependency-path: electron-app/package-lock.json
        
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        
    - name: Cache Python dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
          
    - name: Install system dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y --no-install-recommends \
          libopenjp2-tools \
          rpm \
          bsdtar
          
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller
        
    - name: Create .env file
      run: |
        echo "OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}" > .env
        
    - name: Build Python backend
      run: |
        pyinstaller --onefile --noconsole \
          --hidden-import=langchain \
          --hidden-import=langchain_openai \
          --hidden-import=biopython \
          --hidden-import=uvicorn \
          --hidden-import=starlette \
          --exclude-module=tkinter \
          --exclude-module=matplotlib \
          --distpath=dist \
          src/drug_discovery_agent/chat_server/__main__.py
          
    - name: Install Node.js dependencies
      working-directory: electron-app
      run: npm ci
      
    - name: Build Electron app for Linux
      working-directory: electron-app
      run: npm run build:linux
      
    - name: Upload Linux artifacts
      uses: actions/upload-artifact@v3
      with:
        name: linux-installers
        path: |
          electron-app/dist/*.AppImage
          electron-app/dist/*.deb
          electron-app/dist/*.rpm
        retention-days: 30

  # Job 4: Create Release (only on tags)
  create-release:
    needs: [build-macos, build-windows, build-linux]
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Download all artifacts
      uses: actions/download-artifact@v3
      with:
        path: artifacts
        
    - name: Display structure of downloaded files
      run: ls -la artifacts/
      
    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        files: |
          artifacts/macos-installer/*.dmg
          artifacts/windows-installer/*.exe
          artifacts/linux-installers/*.AppImage
          artifacts/linux-installers/*.deb
          artifacts/linux-installers/*.rpm
        generate_release_notes: true
        draft: false
        prerelease: ${{ contains(github.ref, '-') }}
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 3. Enhanced Package Configuration

### Update electron-app/package.json

To support multiple Linux formats, update the `build` section:

```json
{
  "build": {
    "appId": "deda.drug-evaluation-and-discovery-agent",
    "productName": "Bioinformatics Chat Assistant",
    "directories": {
      "output": "dist",
      "buildResources": "build"
    },
    "files": [
      "main.js",
      "preload.js",
      "src/**/*",
      "!src/**/*.test.js",
      "!**/*.md",
      "python-backend/**/*"
    ],
    "extraResources": [
      {
        "from": "../dist/",
        "to": "python-backend/",
        "filter": ["**/*"]
      }
    ],
    "mac": {
      "category": "public.app-category.education",
      "target": [
        {
          "target": "dmg",
          "arch": ["x64", "arm64"]
        }
      ],
      "icon": "build/icon.icns",
      "hardenedRuntime": true,
      "gatekeeperAssess": false,
      "entitlements": "build/entitlements.mac.plist",
      "entitlementsInherit": "build/entitlements.mac.plist"
    },
    "win": {
      "target": [
        {
          "target": "nsis",
          "arch": ["x64", "ia32"]
        }
      ],
      "icon": "build/icon.ico",
      "publisherName": "Bioinformatics Research Team",
      "verifyUpdateCodeSignature": false
    },
    "linux": {
      "target": [
        {
          "target": "AppImage",
          "arch": ["x64"]
        },
        {
          "target": "deb",
          "arch": ["x64"]
        },
        {
          "target": "rpm",
          "arch": ["x64"]
        }
      ],
      "category": "Science",
      "icon": "build/icon.png",
      "maintainer": "Bioinformatics Research Team",
      "vendor": "Bioinformatics Research Team"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "installerIcon": "build/icon.ico",
      "uninstallerIcon": "build/icon.ico"
    },
    "deb": {
      "depends": [
        "libgtk-3-0",
        "libnotify4",
        "libnss3",
        "libxss1",
        "libxtst6",
        "xdg-utils",
        "libatspi2.0-0",
        "libuuid1",
        "libsecret-1-0"
      ],
      "recommends": [
        "libappindicator3-1"
      ]
    },
    "rpm": {
      "depends": [
        "gtk3",
        "libnotify",
        "nss",
        "libXScrnSaver",
        "libXtst",
        "xdg-utils",
        "at-spi2-core",
        "libuuid"
      ]
    }
  }
}
```

## 4. Additional CI/CD Workflows

### Development Workflow

Create `.github/workflows/dev-build.yml` for development builds:

```yaml
name: Development Build

on:
  push:
    branches: [ develop, feature/* ]

jobs:
  test-build:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    
    runs-on: ${{ matrix.os }}
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        cd electron-app
        npm ci
        
    - name: Run tests
      run: |
        cd electron-app
        npm test
        
    - name: Build (no signing)
      run: |
        cd electron-app
        npm run build
```

### Code Quality Workflow

Create `.github/workflows/code-quality.yml`:

```yaml
name: Code Quality

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  python-quality:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install ruff mypy
        
    - name: Run ruff (linting)
      run: ruff check .
      
    - name: Run ruff (formatting)
      run: ruff format . --check
      
    - name: Run mypy (type checking)
      run: mypy .
      
    - name: Run tests
      run: pytest

  javascript-quality:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        
    - name: Install dependencies
      working-directory: electron-app
      run: npm ci
      
    - name: Run ESLint
      working-directory: electron-app
      run: npm run lint
      
    - name: Run tests
      working-directory: electron-app
      run: npm test
```

## 5. Deployment and Release Management

### Automatic Release Creation

The main workflow automatically creates GitHub releases when you push a tag:

```bash
# Create and push a new release tag
git tag v1.0.0
git push origin v1.0.0
```

### Manual Release Workflow

Create `.github/workflows/manual-release.yml` for manual releases:

```yaml
name: Manual Release

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Release version'
        required: true
        default: '1.0.0'
      prerelease:
        description: 'Is this a prerelease?'
        required: false
        default: 'false'

jobs:
  manual-release:
    uses: ./.github/workflows/build-desktop-apps.yml
    secrets: inherit
    
  create-manual-release:
    needs: manual-release
    runs-on: ubuntu-latest
    
    steps:
    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        tag_name: v${{ github.event.inputs.version }}
        name: Release ${{ github.event.inputs.version }}
        prerelease: ${{ github.event.inputs.prerelease == 'true' }}
```

## 6. Security and Best Practices

### Environment Security
- Never commit secrets to the repository
- Use GitHub's encrypted secrets for sensitive data
- Rotate certificates and API keys regularly
- Use least-privilege access for deployment tokens

### Build Security
- Pin action versions to specific commits for reproducibility
- Use official actions from trusted sources
- Validate checksums of downloaded dependencies
- Scan built artifacts for vulnerabilities

### Dependency Management
- Use `package-lock.json` and `requirements.txt` for reproducible builds
- Regularly update dependencies and scan for vulnerabilities
- Use GitHub's Dependabot for automated dependency updates

## 7. Monitoring and Notifications

### Build Status Badges

Add build status badges to your README.md:

```markdown
[![Build Desktop Applications](https://github.com/your-username/train-a-model/actions/workflows/build-desktop-apps.yml/badge.svg)](https://github.com/your-username/train-a-model/actions/workflows/build-desktop-apps.yml)
```

### Slack/Discord Notifications

Add notification steps to your workflows:

```yaml
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    channel: '#builds'
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

## 8. Troubleshooting CI/CD

### Common Issues and Solutions

1. **Certificate Issues:**
   - Ensure certificates are properly base64 encoded
   - Verify certificate passwords are correct
   - Check certificate expiration dates

2. **Build Failures:**
   - Check runner OS compatibility
   - Verify all dependencies are available
   - Review build logs for specific error messages

3. **Artifact Upload Issues:**
   - Ensure artifact paths are correct
   - Check file permissions and sizes
   - Verify artifact retention policies

4. **Release Creation Issues:**
   - Ensure `GITHUB_TOKEN` has proper permissions
   - Check tag format and naming conventions
   - Verify release notes generation

### Debug Mode

Enable debug logging by setting secrets:
```
ACTIONS_STEP_DEBUG: true
ACTIONS_RUNNER_DEBUG: true
```

## 9. Future Enhancements

### Potential Improvements
- Add automated testing of built installers
- Implement staged deployments (dev → staging → production)
- Add performance benchmarking
- Integrate with package registries (Homebrew, Chocolatey, etc.)
- Add automated security scanning
- Implement blue-green deployments for continuous delivery

### Scaling Considerations
- Use self-hosted runners for faster builds
- Implement build caching strategies
- Add build matrix for multiple versions
- Consider using Docker for consistent environments