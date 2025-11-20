import axios from 'axios';
import config from '../config';

/**
 * Simple API service for chat - no persistence
 */
class ApiService {
  private baseURL: string;

  constructor() {
    this.baseURL = config.apiBaseUrl;
  }

  /**
   * Send a message and get streaming response
   */
  async sendMessage(message: string): Promise<string> {
    try {
      const response = await axios.post(`${this.baseURL}/api/ask`, {
        question: message
      });

      return response.data.answer || '';
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }

  /**
   * Send a message and get streaming response (SSE)
   */
  streamMessage(
    message: string,
    enableWebSearch: boolean,
    onChunk: (chunk: string) => void,
    onComplete: () => void,
    onError: (error: Error) => void
  ): AbortController {
    const abortController = new AbortController();

    fetch(`${this.baseURL}/api/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: message,
        enable_web_search: enableWebSearch
      }),
      signal: abortController.signal,
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No reader available');
        }

        const readChunk = (): Promise<void> => {
          return reader.read().then(({ done, value }) => {
            if (done) {
              onComplete();
              return;
            }

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6); // Don't trim - preserve spaces
                if (data.trim() === '[DONE]') {
                  onComplete();
                  return;
                }
                // Send all chunks, even empty ones (might be spaces)
                onChunk(data);
              }
            }

            return readChunk();
          });
        };

        return readChunk();
      })
      .catch(error => {
        if (error.name !== 'AbortError') {
          onError(error);
        }
      });

    return abortController;
  }
}

// Create and export a singleton instance
const apiService = new ApiService();
export default apiService;
