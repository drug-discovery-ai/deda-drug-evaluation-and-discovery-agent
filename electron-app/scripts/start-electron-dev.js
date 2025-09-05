#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const os = require('os');

/**
 * Platform-aware Electron development starter script
 * Handles platform-specific Electron flags and development setup
 */

function log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const prefix = type === 'error' ? '❌' : type === 'warn' ? '⚠️' : '✅';
    console.log(`[${timestamp}] ${prefix} ${message}`);
}

function getElectronArgs() {
    const platform = os.platform();
    const args = ['.', '--inspect=5858'];
    
    // Add platform-specific flags
    if (platform === 'linux') {
        // Fix for Linux SUID sandbox issues in development
        args.push('--no-sandbox');
        log('Added --no-sandbox flag for Linux development', 'warn');
    }
    
    return args;
}

function startElectronDev() {
    const electronDir = path.resolve(__dirname, '..');
    const args = getElectronArgs();
    
    log('Starting Electron development server...');
    log(`Working directory: ${electronDir}`);
    log(`Platform: ${os.platform()}`);
    log(`Command: electron ${args.join(' ')}`);
    
    // Check if we're in development mode
    const env = {
        ...process.env,
        NODE_ENV: 'development'
    };
    
    // Spawn Electron process
    const electronProcess = spawn('electron', args, {
        cwd: electronDir,
        env: env,
        stdio: 'inherit'
    });
    
    electronProcess.on('error', (error) => {
        if (error.code === 'ENOENT') {
            log('Electron executable not found. Please install electron:', 'error');
            log('  npm install electron --save-dev', 'error');
        } else {
            log(`Failed to start Electron: ${error.message}`, 'error');
        }
        process.exit(1);
    });
    
    electronProcess.on('exit', (code, signal) => {
        if (signal) {
            log(`Electron terminated by signal: ${signal}`, 'warn');
        } else {
            log(`Electron exited with code: ${code}`, code === 0 ? 'info' : 'error');
        }
        process.exit(code || 0);
    });
    
    // Handle graceful shutdown
    process.on('SIGINT', () => {
        log('Received SIGINT, shutting down Electron...');
        electronProcess.kill('SIGTERM');
    });
    
    process.on('SIGTERM', () => {
        log('Received SIGTERM, shutting down Electron...');
        electronProcess.kill('SIGTERM');
    });
}

// Platform-specific warnings and tips
function showPlatformTips() {
    const platform = os.platform();
    
    if (platform === 'linux') {
        log('Linux Development Tips:', 'info');
        log('  - Using --no-sandbox for development (less secure but functional)', 'info');
        log('  - For production, configure proper chrome-sandbox permissions', 'info');
    }
    
    if (platform === 'win32') {
        log('Windows Development Tips:', 'info');
        log('  - Ensure Windows Defender exclusions for faster builds', 'info');
    }
    
    if (platform === 'darwin') {
        log('macOS Development Tips:', 'info');
        log('  - Code signing may be required for some features', 'info');
    }
}

// Run the script
if (require.main === module) {
    showPlatformTips();
    startElectronDev();
}

module.exports = { startElectronDev, getElectronArgs };