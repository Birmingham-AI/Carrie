/**
 * Application configuration
 *
 * Centralized configuration for environment variables and app settings
 */

interface Config {
  apiBaseUrl: string;
}

const config: Config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001',
};

export default config;
