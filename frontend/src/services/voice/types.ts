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
 * Pending function call tracking
 */
export interface PendingFunctionCall {
  name: string;
  arguments: string;
}

/**
 * Event data from Eventbrite
 */
export interface EventbriteEvent {
  name: string;
  start_date: string;
  start_time: string;
  end_time: string;
  location: string;
  description: string;
  tickets_available: number | null;
  price: string | null;
  is_free: boolean;
  url: string;
}

/**
 * Session data from backend
 */
export interface SessionInfo {
  session_info: string;
  chunk_count: number;
}

/**
 * Search result from backend
 */
export interface SearchResult {
  session_info: string;
  timestamp: string;
  score: number;
  text: string;
}
