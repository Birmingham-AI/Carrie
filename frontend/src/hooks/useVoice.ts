import { useState, useEffect, useCallback, useRef } from 'react';
import voiceService, { VoiceEvent } from '../services/VoiceService';

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

  // Handle voice events
  useEffect(() => {
    const unsubscribe = voiceService.onEvent((event: VoiceEvent) => {
      switch (event.type) {
        case 'connected':
          setIsVoiceMode(true);
          setIsConnecting(false);
          setError(null);
          break;

        case 'disconnected':
          setIsVoiceMode(false);
          setIsRecording(false);
          setIsPlaying(false);
          setIsConnecting(false);
          break;

        case 'recording_started':
          setIsRecording(true);
          // Clear previous transcripts when starting new recording
          setUserTranscript('');
          userTranscriptRef.current = '';
          break;

        case 'recording_stopped':
          setIsRecording(false);
          // Trigger user message callback with final transcript
          if (userTranscriptRef.current && onUserMessage) {
            onUserMessage(userTranscriptRef.current);
          }
          break;

        case 'transcript':
          // Update user transcript
          setUserTranscript(event.data as string);
          userTranscriptRef.current = event.data as string;
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
  }, [onUserMessage, onAssistantMessage]);

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
