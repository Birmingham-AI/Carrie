import config from '../config';

/**
 * Simple API service for chat with conversation memory
 */
class ApiService {
  private baseURL: string;

  constructor() {
    this.baseURL = config.apiBaseUrl;
  }

  /**
   * Send a message and get streaming response (SSE)
   */
  streamMessage(
    message: string,
    enableWebSearch: boolean,
    conversationHistory: Array<{ role: string; content: string }>,
    onChunk: (chunk: string) => void,
    onComplete: () => void,
    onError: (error: Error) => void
  ): AbortController {
    const abortController = new AbortController();

    fetch(`${this.baseURL}/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: message,
        messages: conversationHistory,
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
                // Unescape newlines that were escaped in the backend for SSE transport
                const unescapedData = data.replace(/\\n/g, '\n');
                // Send all chunks, even empty ones (might be spaces)
                onChunk(unescapedData);
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
