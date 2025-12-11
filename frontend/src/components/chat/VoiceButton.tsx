import React, { useCallback } from 'react';
import { Mic, MicOff, Loader2, Volume2 } from 'lucide-react';

interface VoiceButtonProps {
  isSupported: boolean;
  isVoiceMode: boolean;
  isRecording: boolean;
  isPlaying: boolean;
  isConnecting: boolean;
  onToggleVoiceMode: () => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
}

/**
 * Push-to-talk voice button component
 * - Click to toggle voice mode on/off
 * - Hold to record when in voice mode
 */
const VoiceButton: React.FC<VoiceButtonProps> = ({
  isSupported,
  isVoiceMode,
  isRecording,
  isPlaying,
  isConnecting,
  onToggleVoiceMode,
  onStartRecording,
  onStopRecording
}) => {
  // Handle mouse/touch events for push-to-talk
  const handleMouseDown = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    if (isVoiceMode && !isPlaying) {
      onStartRecording();
    }
  }, [isVoiceMode, isPlaying, onStartRecording]);

  const handleMouseUp = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    if (isVoiceMode && isRecording) {
      onStopRecording();
    }
  }, [isVoiceMode, isRecording, onStopRecording]);

  // Handle click for toggling voice mode (not push-to-talk)
  const handleClick = useCallback((e: React.MouseEvent) => {
    // Only toggle voice mode if not already in voice mode
    // In voice mode, click is handled by mouseDown/mouseUp for PTT
    if (!isVoiceMode) {
      onToggleVoiceMode();
    }
  }, [isVoiceMode, onToggleVoiceMode]);

  // Handle double-click to exit voice mode
  const handleDoubleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    if (isVoiceMode) {
      onToggleVoiceMode();
    }
  }, [isVoiceMode, onToggleVoiceMode]);

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

  // Playing state (AI speaking)
  if (isPlaying) {
    return (
      <button
        className="p-2 text-green-500 rounded-full"
        title="AI is speaking... Double-click to exit voice mode"
        onDoubleClick={handleDoubleClick}
      >
        <Volume2 className="w-5 h-5 animate-pulse" />
      </button>
    );
  }

  // Recording state
  if (isRecording) {
    return (
      <button
        className="p-2 bg-red-500 text-white rounded-full animate-pulse shadow-lg"
        title="Recording... Release to send"
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchEnd={handleMouseUp}
      >
        <Mic className="w-5 h-5" />
      </button>
    );
  }

  // Voice mode active, ready to record
  if (isVoiceMode) {
    return (
      <button
        className="p-2 text-blue-600 bg-blue-50 rounded-full hover:bg-blue-100 transition-colors"
        title="Hold to speak, double-click to exit voice mode"
        onMouseDown={handleMouseDown}
        onTouchStart={handleMouseDown}
        onDoubleClick={handleDoubleClick}
      >
        <Mic className="w-5 h-5" />
      </button>
    );
  }

  // Voice mode inactive
  return (
    <button
      className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
      title="Click to enable voice mode"
      onClick={handleClick}
    >
      <Mic className="w-5 h-5" />
    </button>
  );
};

export default VoiceButton;
