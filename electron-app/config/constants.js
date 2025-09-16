/**
 * Configuration constants for the Drug Discovery Agent Electron application.
 *
 * This module provides centralized configuration for host and port settings
 * used across the frontend components to communicate with the Python backend.
 */

const DEFAULT_HOST = process.env.SERVER_HOST || '127.0.0.1';
const DEFAULT_PORT = parseInt(process.env.SERVER_PORT || '8080', 10);

const SERVER_CONFIG = {
    HOST: DEFAULT_HOST,
    PORT: DEFAULT_PORT,
    get URL() {
        return `http://${this.HOST}:${this.PORT}`;
    },
    get ENDPOINTS() {
        return {
            HEALTH: `${this.URL}/health`,
            API_KEY_STATUS: `${this.URL}/api/key/status`,
            API_KEY_VALIDATE: `${this.URL}/api/key/validate`,
            API_KEY_MANAGE: `${this.URL}/api/key`,
        };
    }
};

module.exports = {
    SERVER_CONFIG,
    DEFAULT_HOST,
    DEFAULT_PORT
};