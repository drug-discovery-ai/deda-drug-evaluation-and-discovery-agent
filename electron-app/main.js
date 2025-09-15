const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const { existsSync } = require('fs');

class ElectronApp {
    constructor() {
        this.pythonProcess = null;
        this.mainWindow = null;
        this.serverPort = 8080;
        this.serverHost = '127.0.0.1';
        this.baseServerUrl = `http://${this.serverHost}:${this.serverPort}`;
        this.isQuitting = false;
        this.isDevelopment = process.env.NODE_ENV === 'development' || process.defaultApp || /[\\/]electron-prebuilt[\\/]/.test(process.execPath) || /[\\/]electron[\\/]/.test(process.execPath);
    }

    async createWindow() {
        // Create the browser window with security settings
        this.mainWindow = new BrowserWindow({
            width: 1200,
            height: 800,
            minWidth: 800,
            minHeight: 600,
            icon: this.getAppIcon(),
            show: true, // Show window immediately
            titleBarStyle: process.platform === 'darwin' ? 'hidden' : 'default',
            webPreferences: {
                nodeIntegration: false, // Security: disable node integration
                contextIsolation: true, // Security: enable context isolation
                enableRemoteModule: false, // Security: disable remote module
                preload: path.join(__dirname, 'preload.js'), // Load preload script
                webSecurity: true, // Enable web security
                allowRunningInsecureContent: false // Prevent insecure content
            }
        });

        // Load the app
        this.mainWindow.loadFile('views/index.html');

        // Show window when ready to prevent visual flash
        this.mainWindow.once('ready-to-show', () => {
            // Focus on input field after window is ready
            this.mainWindow.webContents.executeJavaScript(`
                const messageInput = document.getElementById('message-input');
                if (messageInput) messageInput.focus();
            `);
        });

        // DevTools can be opened manually with Ctrl+Shift+I or Cmd+Option+I

        // Handle window closed
        this.mainWindow.on('closed', () => {
            this.mainWindow = null;
        });

        // Handle external links
        this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
            shell.openExternal(url);
            return { action: 'deny' };
        });

        // Prevent navigation away from the app
        this.mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
            const parsedUrl = new URL(navigationUrl);
            if (parsedUrl.origin !== 'file://') {
                event.preventDefault();
            }
        });
    }

    getAppIcon() {
        // Return platform-specific icon path
        if (process.platform === 'win32') {
            return path.join(__dirname, '..', 'assets', 'icon.ico');
        } else if (process.platform === 'darwin') {
            return path.join(__dirname, '..', 'assets', 'icon.icns');
        } else {
            return path.join(__dirname, '..', 'assets', 'icon.png');
        }
    }

    async startPythonBackend() {
        return new Promise((resolve, reject) => {
            // Check if we're in development by looking for package.json in parent directory
            const isDev = existsSync(path.join(__dirname, '..', 'package.json')) || 
                         process.env.NODE_ENV === 'development' ||
                         !app.isPackaged;
            
            let pythonCommand;
            let args;

            if (isDev) {
                // Development mode: assume backend is already running
                console.log('Development mode: assuming backend is already running on port', this.serverPort);
                // Just resolve immediately - the backend should already be running
                setTimeout(() => resolve(), 1000);
                return;
            } else {
                // Production mode: use packaged executable
                const executablePath = this.getPythonExecutablePath();
                
                if (!existsSync(executablePath)) {
                    reject(new Error(`Python backend executable not found at: ${executablePath}`));
                    return;
                }

                args = ['--host', this.serverHost, '--port', this.serverPort.toString()];
                this.pythonProcess = spawn(executablePath, args, {
                    stdio: ['pipe', 'pipe', 'pipe']
                });
            }

            // Handle Python process output
            this.pythonProcess.stdout.on('data', (data) => {
                const output = data.toString();
                console.log('Python Backend:', output);
                
                // Check if server started successfully
                if (output.includes('Bioinformatics Chat Server starting') || 
                    output.includes('Ready for stateful Electron frontend connections!')) {
                    // Wait a moment for server to be fully ready, then verify with health check
                    setTimeout(async () => {
                        const isHealthy = await this.healthCheck();
                        if (isHealthy) {
                            resolve();
                        } else {
                            // If health check fails, wait a bit more and try again
                            setTimeout(async () => {
                                const isHealthyRetry = await this.healthCheck();
                                if (isHealthyRetry) {
                                    resolve();
                                } else {
                                    reject(new Error('Backend started but health check failed'));
                                }
                            }, 3000);
                        }
                    }, 2000);
                }
            });

            this.pythonProcess.stderr.on('data', (data) => {
                const error = data.toString();
                console.error('Python Backend Error:', error);
                
                // Don't reject on stderr as some libraries output warnings there
                if (error.toLowerCase().includes('error') && 
                    !error.toLowerCase().includes('warning')) {
                    reject(new Error(`Python backend failed to start: ${error}`));
                }
            });

            this.pythonProcess.on('close', (code) => {
                console.log(`Python backend process exited with code ${code}`);
                // Only show error dialog for unexpected crashes, not normal shutdowns or development restarts
                if (code !== 0 && !this.isQuitting && !this.isDevelopment) {
                    this.showError('Backend Server Error',
                        `The backend server crashed unexpectedly (code: ${code}). Please restart the application.`);
                }
            });

            this.pythonProcess.on('error', (err) => {
                console.error('Failed to start Python backend:', err);
                reject(new Error(`Failed to start Python backend: ${err.message}`));
            });

            // Timeout if server doesn't start within 30 seconds
            setTimeout(() => {
                if (this.pythonProcess && this.pythonProcess.exitCode === null) {
                    reject(new Error('Python backend startup timeout after 30 seconds'));
                }
            }, 30000);
        });
    }

    getPythonExecutablePath() {
        // Return path to PyInstaller executable based on platform
        const resourcesPath = process.resourcesPath;
        
        switch (process.platform) {
            case 'win32':
                return path.join(resourcesPath, 'python-backend', '__main__.exe');
            case 'darwin':
                return path.join(resourcesPath, 'python-backend', '__main__');
            case 'linux':
                return path.join(resourcesPath, 'python-backend', '__main__');
            default:
                throw new Error(`Unsupported platform: ${process.platform}`);
        }
    }

    async healthCheck() {
        // Check if backend server is responding
        try {
            // Try both localhost and 127.0.0.1 to handle IPv4/IPv6 issues
            let response;
            try {
                response = await fetch(`${this.baseServerUrl}/health`);
            } catch (e) {
                response = await fetch(`http://${this.serverHost}:${this.serverPort}/health`);
            }
            return response.ok;
        } catch (error) {
            console.error('Health check failed:', error);
            return false;
        }
    }

    setupIPC() {
        // Handle server status requests from renderer
        ipcMain.handle('get-server-status', async () => {
            const isHealthy = await this.healthCheck();
            return {
                running: !!this.pythonProcess,
                healthy: isHealthy,
                host: this.serverHost,
                port: this.serverPort
            };
        });

        // Handle app version request
        ipcMain.handle('get-app-version', () => {
            return app.getVersion();
        });

        // Handle restart backend request
        ipcMain.handle('restart-backend', async () => {
            try {
                await this.stopPythonBackend();
                await this.startPythonBackend();
                return { success: true };
            } catch (error) {
                return { success: false, error: error.message };
            }
        });

        // Handle API key status check
        ipcMain.handle('check-api-key-status', async () => {
            try {
                const response = await fetch(`${this.baseServerUrl}/api/key/status`);
                if (response.ok) {
                    return await response.json();
                } else {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            } catch (error) {
                console.error('Failed to check API key status:', error);
                return { has_key: false, source: 'none', error: error.message };
            }
        });

    }

    async stopPythonBackend() {
        return new Promise((resolve) => {
            if (this.pythonProcess) {
                this.pythonProcess.on('close', () => {
                    this.pythonProcess = null;
                    resolve();
                });

                // Try graceful shutdown first
                this.pythonProcess.kill('SIGTERM');

                // Force kill after 5 seconds
                setTimeout(() => {
                    if (this.pythonProcess) {
                        this.pythonProcess.kill('SIGKILL');
                        this.pythonProcess = null;
                        resolve();
                    }
                }, 5000);
            } else {
                // No process to stop (likely development mode)
                resolve();
            }
        });
    }

    showError(title, message) {
        if (this.mainWindow && this.mainWindow.webContents) {
            // Send error to renderer for toast notification instead of native dialog
            this.mainWindow.webContents.send('show-error-notification', {
                title,
                message,
                type: 'error'
            });
        }
    }

    async initialize() {
        try {
            // Set up IPC handlers
            this.setupIPC();

            // Create main window first so user sees something immediately
            await this.createWindow();
            console.log('Electron window created');

            // Start Python backend in parallel
            console.log('Starting Python backend server...');
            await this.startPythonBackend();
            console.log('Python backend started successfully');

            // Verify backend is healthy
            const isHealthy = await this.healthCheck();
            if (!isHealthy) {
                throw new Error('Backend server is not responding to health checks');
            }

            console.log('Application initialized successfully');
        } catch (error) {
            console.error('Failed to initialize application:', error);
            this.showError('Startup Error', 
                `Failed to start the application: ${error.message}`);
            app.quit();
        }
    }
}

// Create application instance
const electronApp = new ElectronApp();

// Ensure single instance
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
    // Another instance is already running, quit this one
    app.quit();
} else {
    // Handle second instance attempts
    app.on('second-instance', (event, commandLine, workingDirectory) => {
        // Someone tried to run a second instance, focus our window instead
        if (electronApp.mainWindow) {
            if (electronApp.mainWindow.isMinimized()) {
                electronApp.mainWindow.restore();
            }
            electronApp.mainWindow.focus();
        }
    });
}

// App event handlers (outside the single instance check)
app.whenReady().then(() => {
    electronApp.initialize();
});

app.on('activate', () => {
    // On macOS, show and focus existing window when dock icon is clicked
    if (electronApp.mainWindow && !electronApp.mainWindow.isDestroyed()) {
        // Existing window - show and focus it
        if (!electronApp.mainWindow.isVisible()) {
            electronApp.mainWindow.show();
        }
        electronApp.mainWindow.focus();
    } else if (BrowserWindow.getAllWindows().length === 0) {
        // No windows at all - create new one
        electronApp.createWindow();
    }
    // If windows exist but mainWindow is null, do nothing (edge case)
});

app.on('window-all-closed', () => {
    // On macOS, keep app running even when all windows are closed
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', async (event) => {
    if (!electronApp.isQuitting) {
        electronApp.isQuitting = true;
        event.preventDefault();

        console.log('Shutting down application...');
        
        try {
            // Stop Python backend gracefully
            await electronApp.stopPythonBackend();
            console.log('Python backend stopped');
        } catch (error) {
            console.error('Error stopping Python backend:', error);
        }

        // Now actually quit
        app.quit();
    }
});

// Security: Prevent new window creation
app.on('web-contents-created', (event, contents) => {
    contents.on('new-window', (event, navigationUrl) => {
        event.preventDefault();
        shell.openExternal(navigationUrl);
    });
});

// Handle certificate errors
app.on('certificate-error', (event, webContents, url, error, certificate, callback) => {
    // In development, ignore certificate errors for localhost
    if (process.env.NODE_ENV === 'development' && url.startsWith('http://localhost')) {
        event.preventDefault();
        callback(true);
    } else {
        callback(false);
    }
});

module.exports = ElectronApp;