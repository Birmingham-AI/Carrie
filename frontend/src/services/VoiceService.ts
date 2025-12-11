import config from '../config';

/**
 * Voice event types for callbacks
 */
export type VoiceEventType =
  | 'connected'
  | 'disconnected'
  | 'recording_started'
  | 'recording_stopped'
  | 'transcript'
  | 'response_text'
  | 'response_audio_started'
  | 'response_audio_ended'
  | 'error'
  | 'function_call';

export interface VoiceEvent {
  type: VoiceEventType;
  data?: string | object;
}

export type VoiceEventCallback = (event: VoiceEvent) => void;

/**
 * VoiceService manages WebRTC connection to OpenAI Realtime API
 * for speech-to-speech interaction with function calling support.
 */
class VoiceService {
  private peerConnection: RTCPeerConnection | null = null;
  private dataChannel: RTCDataChannel | null = null;
  private mediaStream: MediaStream | null = null;
  private audioElement: HTMLAudioElement | null = null;
  private eventCallbacks: VoiceEventCallback[] = [];
  private isConnected = false;
  private pendingFunctionCalls: Map<string, { name: string; arguments: string }> = new Map();

  /**
   * Subscribe to voice events
   */
  onEvent(callback: VoiceEventCallback): () => void {
    this.eventCallbacks.push(callback);
    return () => {
      this.eventCallbacks = this.eventCallbacks.filter(cb => cb !== callback);
    };
  }

  private emit(event: VoiceEvent): void {
    this.eventCallbacks.forEach(cb => cb(event));
  }

  /**
   * Check if WebRTC and getUserMedia are supported
   */
  isSupported(): boolean {
    return !!(
      typeof RTCPeerConnection !== 'undefined' &&
      navigator.mediaDevices &&
      navigator.mediaDevices.getUserMedia
    );
  }

  /**
   * Get current connection status
   */
  getIsConnected(): boolean {
    return this.isConnected;
  }

  /**
   * Connect to OpenAI Realtime API via WebRTC
   */
  async connect(): Promise<void> {
    if (this.isConnected) {
      console.warn('VoiceService: Already connected');
      return;
    }

    try {
      // Step 1: Get ephemeral token from backend
      const sessionResponse = await fetch(`${config.apiBaseUrl}/v1/realtime/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!sessionResponse.ok) {
        throw new Error(`Failed to create session: ${sessionResponse.statusText}`);
      }

      const sessionData = await sessionResponse.json();
      const ephemeralKey = sessionData.client_secret?.value;

      if (!ephemeralKey) {
        throw new Error('No ephemeral key received from backend');
      }

      // Step 2: Get microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 24000
        }
      });

      // Step 3: Create peer connection
      this.peerConnection = new RTCPeerConnection();

      // Add audio track from microphone
      const audioTrack = this.mediaStream.getAudioTracks()[0];
      this.peerConnection.addTrack(audioTrack, this.mediaStream);

      // Set up audio playback for incoming audio
      this.audioElement = document.createElement('audio');
      this.audioElement.autoplay = true;

      this.peerConnection.ontrack = (event) => {
        if (this.audioElement && event.streams[0]) {
          this.audioElement.srcObject = event.streams[0];
        }
      };

      // Create data channel for events
      this.dataChannel = this.peerConnection.createDataChannel('oai-events');
      this.setupDataChannelHandlers();

      // Step 4: Create and set local offer
      const offer = await this.peerConnection.createOffer();
      await this.peerConnection.setLocalDescription(offer);

      // Step 5: Send offer to OpenAI and get answer
      const sdpResponse = await fetch(
        'https://api.openai.com/v1/realtime?model=gpt-realtime',
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${ephemeralKey}`,
            'Content-Type': 'application/sdp'
          },
          body: offer.sdp
        }
      );

      if (!sdpResponse.ok) {
        throw new Error(`Failed to establish WebRTC connection: ${sdpResponse.statusText}`);
      }

      const answerSdp = await sdpResponse.text();

      // Step 6: Set remote description
      await this.peerConnection.setRemoteDescription({
        type: 'answer',
        sdp: answerSdp
      });

      this.isConnected = true;
      this.emit({ type: 'connected' });

    } catch (error) {
      this.cleanup();
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.emit({ type: 'error', data: errorMessage });
      throw error;
    }
  }

  /**
   * Set up handlers for the data channel
   */
  private setupDataChannelHandlers(): void {
    if (!this.dataChannel) return;

    this.dataChannel.onopen = () => {};
    this.dataChannel.onclose = () => {};

    this.dataChannel.onmessage = async (event) => {
      try {
        const message = JSON.parse(event.data);
        await this.handleRealtimeEvent(message);
      } catch (error) {
        // Silent fail on parse errors
      }
    };
  }

  /**
   * Handle events from OpenAI Realtime API
   */
  private async handleRealtimeEvent(event: { type: string; [key: string]: unknown }): Promise<void> {
    switch (event.type) {
      case 'conversation.item.input_audio_transcription.completed':
        // User's speech transcribed
        this.emit({
          type: 'transcript',
          data: event.transcript as string
        });
        break;

      case 'response.text.delta':
        // Streaming text response
        this.emit({
          type: 'response_text',
          data: event.delta as string
        });
        break;

      case 'response.audio.delta':
        // Audio is being streamed (handled by WebRTC track)
        break;

      case 'response.audio_transcript.delta':
        // Transcript of audio response
        this.emit({
          type: 'response_text',
          data: event.delta as string
        });
        break;

      case 'response.output_item.added':
        // Handle different output item types
        {
          const item = event.item as { id?: string; type?: string; name?: string; call_id?: string };
          if (item?.type === 'message') {
            this.emit({ type: 'response_audio_started' });
          } else if (item?.type === 'function_call' && item?.call_id) {
            // Capture function name when output item is added
            this.pendingFunctionCalls.set(item.call_id, {
              name: item.name || '',
              arguments: ''
            });
          }
        }
        break;

      case 'response.done':
        this.emit({ type: 'response_audio_ended' });
        break;

      case 'response.function_call_arguments.delta':
        // Accumulate function call arguments
        {
          const callId = event.call_id as string;
          const existing = this.pendingFunctionCalls.get(callId);
          if (existing) {
            existing.arguments += event.delta as string;
            // Update name if provided in this event
            if (event.name) {
              existing.name = event.name as string;
            }
          } else {
            this.pendingFunctionCalls.set(callId, {
              name: event.name as string || '',
              arguments: event.delta as string || ''
            });
          }
        }
        break;

      case 'response.function_call_arguments.done':
        // Function call complete, execute it
        {
          const callId = event.call_id as string;
          const functionCall = this.pendingFunctionCalls.get(callId) || {
            name: event.name as string,
            arguments: event.arguments as string
          };
          this.pendingFunctionCalls.delete(callId);

          this.emit({
            type: 'function_call',
            data: { callId, ...functionCall }
          });

          // Execute the function and send result back
          const funcName = functionCall.name || event.name as string;
          const funcArgs = functionCall.arguments || event.arguments as string;
          if (funcName) {
            await this.executeFunctionCall(callId, funcName, funcArgs);
          }
        }
        break;

      case 'error':
        this.emit({
          type: 'error',
          data: (event.error as { message?: string })?.message || 'Unknown error'
        });
        break;
    }
  }

  /**
   * Execute a function call and send result back to OpenAI
   */
  private async executeFunctionCall(callId: string, name: string, argsJson: string): Promise<void> {
    try {
      const args = JSON.parse(argsJson || '{}');

      if (name === 'meeting_notes') {
        const action = args.action;

        if (action === 'list_sessions') {
          const params = new URLSearchParams();
          if (args.filter) {
            params.append('filter', args.filter);
          }

          const sessionsUrl = `${config.apiBaseUrl}/v1/sessions${params.toString() ? '?' + params : ''}`;
          const response = await fetch(sessionsUrl);

          if (!response.ok) {
            this.sendFunctionResult(callId, `Failed to list sessions: ${response.statusText}`);
            return;
          }

          const data = await response.json();

          let output: string;
          if (data.sessions && data.sessions.length > 0) {
            output = `Found ${data.sessions.length} session(s):\n` +
              data.sessions.map((s: { session_info: string; chunk_count: number }, i: number) =>
                `${i + 1}. ${s.session_info} (${s.chunk_count} chunks)`
              ).join('\n');
          } else {
            output = 'No sessions found matching the filter.';
          }

          this.sendFunctionResult(callId, output);

        } else if (action === 'search') {
          const params = new URLSearchParams({
            question: args.query || '',
            top_k: String(args.top_k || 5)
          });

          if (args.session_filter) {
            params.append('session_filter', args.session_filter);
          }

          const searchUrl = `${config.apiBaseUrl}/v1/search?${params}`;
          const response = await fetch(searchUrl);

          if (!response.ok) {
            this.sendFunctionResult(callId, `Search failed: ${response.statusText}`);
            return;
          }

          const results = await response.json();

          let output: string;
          if (results.results && results.results.length > 0) {
            output = results.results.map((r: { session_info: string; timestamp: string; score: number; text: string }, i: number) =>
              `${i + 1}. [Session: ${r.session_info}, Timestamp: ${r.timestamp}, Score: ${r.score.toFixed(3)}]\n   ${r.text}`
            ).join('\n\n');
          } else {
            output = 'No relevant meeting notes found for this query.';
          }

          this.sendFunctionResult(callId, output);

        } else {
          this.sendFunctionResult(callId, `Unknown action: ${action}. Use 'list_sessions' or 'search'.`);
        }

      } else {
        this.sendFunctionResult(callId, `Unknown function: ${name}`);
      }
    } catch (error) {
      this.sendFunctionResult(callId, 'Error executing function: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  }

  /**
   * Send function call result back to OpenAI
   */
  private sendFunctionResult(callId: string, output: string): void {
    if (!this.dataChannel || this.dataChannel.readyState !== 'open') {
      console.error('VoiceService: Data channel not ready');
      return;
    }

    // Create function output item
    this.dataChannel.send(JSON.stringify({
      type: 'conversation.item.create',
      item: {
        type: 'function_call_output',
        call_id: callId,
        output: output
      }
    }));

    // Request a response
    this.dataChannel.send(JSON.stringify({
      type: 'response.create'
    }));
  }

  /**
   * Commit audio buffer and request response (for push-to-talk)
   */
  commitAudioAndRespond(): void {
    if (!this.dataChannel || this.dataChannel.readyState !== 'open') {
      console.warn('VoiceService: Data channel not ready');
      return;
    }

    // Commit the audio buffer
    this.dataChannel.send(JSON.stringify({
      type: 'input_audio_buffer.commit'
    }));

    // Request a response
    this.dataChannel.send(JSON.stringify({
      type: 'response.create'
    }));

    this.emit({ type: 'recording_stopped' });
  }

  /**
   * Clear audio buffer (cancel current recording)
   */
  clearAudioBuffer(): void {
    if (!this.dataChannel || this.dataChannel.readyState !== 'open') {
      return;
    }

    this.dataChannel.send(JSON.stringify({
      type: 'input_audio_buffer.clear'
    }));
  }

  /**
   * Start recording indicator (audio is continuously sent via WebRTC)
   */
  startRecording(): void {
    this.emit({ type: 'recording_started' });
  }

  /**
   * Stop recording and commit audio
   */
  stopRecording(): void {
    this.commitAudioAndRespond();
  }

  /**
   * Cancel the current response
   */
  cancelResponse(): void {
    if (!this.dataChannel || this.dataChannel.readyState !== 'open') {
      return;
    }

    this.dataChannel.send(JSON.stringify({
      type: 'response.cancel'
    }));
  }

  /**
   * Disconnect and cleanup
   */
  disconnect(): void {
    this.cleanup();
    this.isConnected = false;
    this.emit({ type: 'disconnected' });
  }

  /**
   * Cleanup resources
   */
  private cleanup(): void {
    if (this.dataChannel) {
      this.dataChannel.close();
      this.dataChannel = null;
    }

    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }

    if (this.audioElement) {
      this.audioElement.srcObject = null;
      this.audioElement = null;
    }

    this.pendingFunctionCalls.clear();
    this.isConnected = false;
  }
}

// Export singleton instance
const voiceService = new VoiceService();
export default voiceService;
