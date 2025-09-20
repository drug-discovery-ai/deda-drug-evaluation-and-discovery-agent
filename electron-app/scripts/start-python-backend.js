#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

/**
 * Cross-platform Python backend starter script
 * Handles virtual environment activation and backend server startup
 * across Windows, macOS, and Linux platforms
 */

function log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const prefix = type === 'error' ? '❌' : type === 'warn' ? '⚠️' : '✅';
    console.log(`[${timestamp}] ${prefix} ${message}`);
}

function getPythonExecutable() {
    const platform = os.platform();
    const parentDir = path.resolve(__dirname, '../..');
    
    if (platform === 'win32') {
        return path.join(parentDir, 'venv', 'Scripts', 'python.exe');
    } else {
        return path.join(parentDir, 'venv', 'bin', 'python');
    }
}

function checkVirtualEnvironment() {
    const pythonPath = getPythonExecutable();
    
    if (!fs.existsSync(pythonPath)) {
        log(`Virtual environment not found at: ${pythonPath}`, 'error');
        log('Please create a virtual environment by running:', 'error');
        log('  python -m venv venv', 'error');
        log('  pip install -r requirements.txt', 'error');
        process.exit(1);
    }
    
    log(`Found Python executable: ${pythonPath}`);
    return pythonPath;
}

function startPythonBackend() {
    const pythonPath = checkVirtualEnvironment();
    const parentDir = path.resolve(__dirname, '../..');
    
    // Set up environment variables
    const env = {
        ...process.env,
        PYTHONPATH: 'src'
    };
    
    // Command arguments
    const { DEFAULT_PORT } = require('../config/constants');
    const args = ['-m', 'drug_discovery_agent.chat_server', '--port', DEFAULT_PORT.toString()];
    
    log('Starting Python backend server...');
    log(`Command: ${pythonPath} ${args.join(' ')}`);
    log(`Working directory: ${parentDir}`);
    log(`PYTHONPATH: ${env.PYTHONPATH}`);
    
    // Spawn the Python process
    const pythonProcess = spawn(pythonPath, args, {
        cwd: parentDir,
        env: env,
        stdio: 'inherit'
    });
    
    pythonProcess.on('error', (error) => {
        log(`Failed to start Python backend: ${error.message}`, 'error');
        process.exit(1);
    });
    
    pythonProcess.on('exit', (code, signal) => {
        if (signal) {
            log(`Python backend terminated by signal: ${signal}`, 'warn');
        } else {
            log(`Python backend exited with code: ${code}`, code === 0 ? 'info' : 'error');
        }
        process.exit(code || 0);
    });
    
    // Handle graceful shutdown
    process.on('SIGINT', () => {
        log('Received SIGINT, shutting down Python backend...');
        pythonProcess.kill('SIGTERM');
    });
    
    process.on('SIGTERM', () => {
        log('Received SIGTERM, shutting down Python backend...');
        pythonProcess.kill('SIGTERM');
    });
}

// Run the script
if (require.main === module) {
    startPythonBackend();
}

module.exports = { startPythonBackend, getPythonExecutable, checkVirtualEnvironment };