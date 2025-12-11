/**
 * Simple chat message interface
 */
export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  traceId?: string;  // For assistant messages, used for feedback
  isVoice?: boolean; // Whether this message was from voice interaction
}

/**
 * Voice props passed to MessageInput
 */
export interface VoiceInputProps {
  isSupported: boolean;
  isVoiceMode: boolean;
  isConnecting: boolean;
  onToggleVoiceMode: () => void;
}

/**
 * Props for the MessageInput component
 */
export interface MessageInputProps {
  inputMessage: string;
  setInputMessage: (message: string) => void;
  handleSendMessage: (enableWebSearch?: boolean) => void;
  isLoading: boolean;
  cancelStreaming?: () => void;
  onNewChat?: () => void;
  voiceProps?: VoiceInputProps;
}
