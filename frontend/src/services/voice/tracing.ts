/**
 * Voice Tracing Service
 *
 * Sends voice events to the backend for Langfuse observability.
 * Since voice mode uses WebRTC (browser -> OpenAI directly),
 * we send events here for tracing.
 */

import config from '../../config';

type VoiceEventType = 'user_transcript' | 'assistant_response' | 'function_call';

interface TraceState {
  traceId: string;
  sessionId: string;
  startTime: number;
  messageCount: number;
  enabled: boolean;
}

let traceState: TraceState | null = null;

/**
 * Start a new voice trace session
 */
export async function startVoiceTrace(): Promise<string> {
  const sessionId = `voice-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

  try {
    const response = await fetch(`${config.apiBaseUrl}/v1/voice/trace/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });

    if (!response.ok) {
      console.warn('Failed to start voice trace');
      return '';
    }

    const data = await response.json();

    if (data.enabled && data.trace_id) {
      traceState = {
        traceId: data.trace_id,
        sessionId,
        startTime: Date.now(),
        messageCount: 0,
        enabled: true
      };
      return data.trace_id;
    }

    return '';
  } catch (error) {
    console.warn('Voice tracing unavailable:', error);
    return '';
  }
}

/**
 * Log a voice event
 */
export async function logVoiceEvent(
  eventType: VoiceEventType,
  content: string,
  metadata?: Record<string, unknown>
): Promise<void> {
  if (!traceState?.enabled) return;

  traceState.messageCount++;

  try {
    await fetch(`${config.apiBaseUrl}/v1/voice/trace/event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        trace_id: traceState.traceId,
        event_type: eventType,
        content,
        metadata
      })
    });
  } catch (error) {
    console.warn('Failed to log voice event:', error);
  }
}

/**
 * End the voice trace session
 */
export async function endVoiceTrace(): Promise<void> {
  if (!traceState?.enabled) {
    traceState = null;
    return;
  }

  const durationMs = Date.now() - traceState.startTime;
  const messageCount = traceState.messageCount;
  const traceId = traceState.traceId;

  traceState = null;

  try {
    await fetch(`${config.apiBaseUrl}/v1/voice/trace/end`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        trace_id: traceId,
        duration_ms: durationMs,
        message_count: messageCount
      })
    });
  } catch (error) {
    console.warn('Failed to end voice trace:', error);
  }
}

/**
 * Check if tracing is active
 */
export function isTracingActive(): boolean {
  return traceState?.enabled ?? false;
}
