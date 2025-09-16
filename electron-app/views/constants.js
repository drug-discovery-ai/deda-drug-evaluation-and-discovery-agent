/**
 * Browser-side constants for the Drug Discovery Agent frontend.
 *
 * This module provides configuration constants that can be used
 * in the browser renderer process.
 */

const SERVER_CONFIG = {
    HOST: '127.0.0.1',
    PORT: 8080,
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