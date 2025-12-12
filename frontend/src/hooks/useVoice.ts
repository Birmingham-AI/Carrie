import { useState, useEffect, useCallback, useRef } from 'react';
import voiceService, { VoiceEvent } from '../services/voice';

const INACTIVITY_TIMEOUT_MS = 3 * 60 * 1000; // 3 minutes

export interface UseVoiceReturn {
  /** Whether voice is supported in this browser */
  isSupported: boolean;
  /** Whether voice mode is currently active (connected) */
  isVoiceMode: boolean;
  /** Whether currently recording user speech */
  isRecording: boolean;
  /** Whether AI is currently speaking */
  isPlaying: boolean;
  /** Whether connection is in progress */
  isConnecting: boolean;
  /** Real-time transcript of user speech */
  userTranscript: string;
  /** Accumulated text of assistant response */
  assistantResponse: string;
  /** Current error message, if any */
  error: string | null;
  /** Toggle voice mode on/off */
  toggleVoiceMode: () => Promise<void>;
  /** Start recording (for push-to-talk) */
  startRecording: () => void;
  /** Stop recording and send */
  stopRecording: () => void;
  /** Cancel current response */
  cancelResponse: () => void;
  /** Clear transcripts for new turn */
  clearTranscripts: () => void;
}

/**
 * Custom hook for managing voice interaction state
 */
export function useVoice(
  onUserMessage?: (content: string) => void,
  onAssistantMessage?: (content: string) => void
): UseVoiceReturn {
  const [isSupported] = useState(() => voiceService.isSupported());
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [userTranscript, setUserTranscript] = useState('');
  const [assistantResponse, setAssistantResponse] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Use refs to track accumulated values for callbacks
  const userTranscriptRef = useRef('');
  const assistantResponseRef = useRef('');
  const inactivityTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Reset inactivity timeout
  const resetInactivityTimeout = useCallback(() => {
    if (inactivityTimeoutRef.current) {
      clearTimeout(inactivityTimeoutRef.current);
    }
    inactivityTimeoutRef.current = setTimeout(() => {
      console.log('Voice mode disconnected due to inactivity');
      voiceService.disconnect();
    }, INACTIVITY_TIMEOUT_MS);
  }, []);

  // Clear inactivity timeout
  const clearInactivityTimeout = useCallback(() => {
    if (inactivityTimeoutRef.current) {
      clearTimeout(inactivityTimeoutRef.current);
      inactivityTimeoutRef.current = null;
    }
  }, []);

  // Handle voice events
  useEffect(() => {
    const unsubscribe = voiceService.onEvent((event: VoiceEvent) => {
      switch (event.type) {
        case 'connected':
          setIsVoiceMode(true);
          setIsConnecting(false);
          setError(null);
          resetInactivityTimeout();
          break;

        case 'disconnected':
          setIsVoiceMode(false);
          setIsRecording(false);
          setIsPlaying(false);
          setIsConnecting(false);
          clearInactivityTimeout();
          break;

        case 'recording_started':
          setIsRecording(true);
          clearInactivityTimeout(); // Pause timeout while recording
          // Clear previous transcripts when starting new recording
          setUserTranscript('');
          userTranscriptRef.current = '';
          break;

        case 'recording_stopped':
          setIsRecording(false);
          break;

        case 'transcript':
          // User's speech has been transcribed - add to chat
          {
            const transcript = event.data as string;
            setUserTranscript(transcript);
            userTranscriptRef.current = transcript;
            // Trigger user message callback when transcript arrives
            if (transcript && onUserMessage) {
              onUserMessage(transcript);
            }
          }
          break;

        case 'response_text':
          // Accumulate assistant response
          setAssistantResponse(prev => {
            const updated = prev + (event.data as string);
            assistantResponseRef.current = updated;
            return updated;
          });
          break;

        case 'response_audio_started':
          setIsPlaying(true);
          // Clear previous response when new one starts
          setAssistantResponse('');
          assistantResponseRef.current = '';
          break;

        case 'response_audio_ended':
          setIsPlaying(false);
          // Trigger assistant message callback with final response
          if (assistantResponseRef.current && onAssistantMessage) {
            onAssistantMessage(assistantResponseRef.current);
          }
          resetInactivityTimeout(); // Reset timeout after response completes
          break;

        case 'error':
          setError(event.data as string);
          setIsConnecting(false);
          break;

        case 'function_call':
          // Function calls are handled internally by VoiceService
          break;
      }
    });

    return unsubscribe;
  }, [onUserMessage, onAssistantMessage, resetInactivityTimeout, clearInactivityTimeout]);

  const toggleVoiceMode = useCallback(async () => {
    if (isVoiceMode) {
      voiceService.disconnect();
    } else {
      try {
        setIsConnecting(true);
        setError(null);
        await voiceService.connect();
      } catch (err) {
        setIsConnecting(false);
        setError(err instanceof Error ? err.message : 'Failed to connect');
      }
    }
  }, [isVoiceMode]);

  const startRecording = useCallback(() => {
    if (!isVoiceMode) return;
    voiceService.startRecording();
  }, [isVoiceMode]);

  const stopRecording = useCallback(() => {
    if (!isVoiceMode) return;
    voiceService.stopRecording();
  }, [isVoiceMode]);

  const cancelResponse = useCallback(() => {
    if (!isVoiceMode) return;
    voiceService.cancelResponse();
    setIsPlaying(false);
  }, [isVoiceMode]);

  const clearTranscripts = useCallback(() => {
    setUserTranscript('');
    setAssistantResponse('');
    userTranscriptRef.current = '';
    assistantResponseRef.current = '';
  }, []);

  return {
    isSupported,
    isVoiceMode,
    isRecording,
    isPlaying,
    isConnecting,
    userTranscript,
    assistantResponse,
    error,
    toggleVoiceMode,
    startRecording,
    stopRecording,
    cancelResponse,
    clearTranscripts
  };
}

export default useVoice;
