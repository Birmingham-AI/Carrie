import type { VoiceEvent, VoiceEventCallback, PendingFunctionCall } from './types';
import { createConnection, cleanupConnection, sendMessage, isWebRTCSupported, ConnectionResources } from './connection';
import { handleRealtimeEvent } from './eventHandlers';

/**
 * VoiceService manages WebRTC connection to OpenAI Realtime API
 * for speech-to-speech interaction with function calling support.
 */
class VoiceService {
  private resources: Partial<ConnectionResources> = {};
  private eventCallbacks: VoiceEventCallback[] = [];
  private isConnected = false;
  private pendingFunctionCalls: Map<string, PendingFunctionCall> = new Map();

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
    return isWebRTCSupported();
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
      this.resources = await createConnection((event) => {
        this.handleDataChannelMessage(event);
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
   * Handle data channel messages
   */
  private async handleDataChannelMessage(event: MessageEvent): Promise<void> {
    try {
      const message = JSON.parse(event.data);
      await handleRealtimeEvent(message, {
        emit: (e) => this.emit(e),
        sendFunctionResult: (callId, output) => this.sendFunctionResult(callId, output),
        pendingFunctionCalls: this.pendingFunctionCalls
      });
    } catch {
      // Silent fail on parse errors
    }
  }

  /**
   * Send function call result back to OpenAI
   */
  private sendFunctionResult(callId: string, output: string): void {
    const { dataChannel } = this.resources;

    if (!sendMessage(dataChannel || null, {
      type: 'conversation.item.create',
      item: {
        type: 'function_call_output',
        call_id: callId,
        output: output
      }
    })) {
      console.error('VoiceService: Data channel not ready');
      return;
    }

    sendMessage(dataChannel || null, { type: 'response.create' });
  }

  /**
   * Commit audio buffer and request response
   */
  commitAudioAndRespond(): void {
    const { dataChannel } = this.resources;

    if (!sendMessage(dataChannel || null, { type: 'input_audio_buffer.commit' })) {
      console.warn('VoiceService: Data channel not ready');
      return;
    }

    sendMessage(dataChannel || null, { type: 'response.create' });
    this.emit({ type: 'recording_stopped' });
  }

  /**
   * Clear audio buffer
   */
  clearAudioBuffer(): void {
    const { dataChannel } = this.resources;
    sendMessage(dataChannel || null, { type: 'input_audio_buffer.clear' });
  }

  /**
   * Start recording indicator
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
    const { dataChannel } = this.resources;
    sendMessage(dataChannel || null, { type: 'response.cancel' });
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
    cleanupConnection(this.resources);
    this.resources = {};
    this.pendingFunctionCalls.clear();
    this.isConnected = false;
  }
}

export default VoiceService;
