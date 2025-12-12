import React from 'react';
import { Mic, MicOff, Loader2, Square } from 'lucide-react';

interface VoiceButtonProps {
  isSupported: boolean;
  isVoiceMode: boolean;
  isConnecting: boolean;
  onToggleVoiceMode: () => void;
}

/**
 * Voice button component
 * - Click mic to enable voice mode (auto-listens via VAD)
 * - Click stop button to exit voice mode
 */
const VoiceButton: React.FC<VoiceButtonProps> = ({
  isSupported,
  isVoiceMode,
  isConnecting,
  onToggleVoiceMode
}) => {

  if (!isSupported) {
    return (
      <button
        disabled
        className="p-2 text-gray-300 rounded-full cursor-not-allowed"
        title="Voice not supported in this browser"
      >
        <MicOff className="w-5 h-5" />
      </button>
    );
  }

  // Connecting state
  if (isConnecting) {
    return (
      <button
        disabled
        className="p-2 text-blue-400 rounded-full animate-pulse"
        title="Connecting..."
      >
        <Loader2 className="w-5 h-5 animate-spin" />
      </button>
    );
  }

  // Voice mode active - just show stop button
  if (isVoiceMode) {
    return (
      <button
        onClick={onToggleVoiceMode}
        className="p-2 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
        title="Stop voice mode"
      >
        <Square className="w-4 h-4 fill-current" />
      </button>
    );
  }

  // Voice mode inactive
  return (
    <button
      className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
      title="Click to enable voice mode"
      onClick={onToggleVoiceMode}
    >
      <Mic className="w-5 h-5" />
    </button>
  );
};

export default VoiceButton;
