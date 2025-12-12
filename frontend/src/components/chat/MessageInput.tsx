import React, { useState, useRef, useEffect } from 'react';
import { Square, Plus, Globe } from 'lucide-react';
import { MessageInputProps } from '../../types/chat';
import VoiceButton from './VoiceButton';

/**
 * Component for handling user input
 */
const MessageInput: React.FC<MessageInputProps> = ({
  inputMessage,
  setInputMessage,
  handleSendMessage,
  isLoading,
  cancelStreaming,
  onNewChat,
  voiceProps
}) => {
  const [enableWebSearch, setEnableWebSearch] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus input when loading completes
  useEffect(() => {
    if (!isLoading) {
      textareaRef.current?.focus();
    }
  }, [isLoading]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(enableWebSearch);
    }
  };

  return (
    <div className="p-4 pb-6">
      <div className="mx-auto max-w-6xl">
        <div className="flex items-center gap-2 w-full">
          <div className="flex-1 flex items-center bg-white rounded-full border border-gray-200 shadow-lg hover:shadow-xl transition-shadow px-4 py-1.5">
            {/* Web Search Toggle Icon */}
            <button
              onClick={() => setEnableWebSearch(!enableWebSearch)}
              className={`p-2 transition-colors rounded-full ${
                enableWebSearch
                  ? 'text-blue-600 hover:bg-blue-50'
                  : 'text-gray-400 hover:bg-gray-100'
              }`}
              title={enableWebSearch ? 'Web search enabled - Click to disable' : 'Web search disabled - Click to enable'}
            >
              <Globe className="w-5 h-5" />
            </button>

            {/* Message Input */}
            <textarea
              ref={textareaRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder={voiceProps?.isVoiceMode ? "Listening... or type here" : "Ask a question..."}
              className="flex-1 py-2 px-2 bg-transparent border-none focus:outline-none resize-none min-h-[40px] max-h-[200px] text-gray-700 placeholder-gray-400"
              disabled={isLoading}
              rows={1}
              style={{
                height: 'auto',
                overflowY: inputMessage.split('\n').length > 5 ? 'auto' : 'hidden'
              }}
            />

            {/* Voice Button */}
            {voiceProps && (
              <VoiceButton
                isSupported={voiceProps.isSupported}
                isVoiceMode={voiceProps.isVoiceMode}
                isConnecting={voiceProps.isConnecting}
                onToggleVoiceMode={voiceProps.onToggleVoiceMode}
              />
            )}

            {/* Stop Button (when streaming) */}
            {isLoading && (
              <button
                onClick={cancelStreaming}
                className="p-2.5 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors shadow-md hover:shadow-lg flex-shrink-0"
                title="Stop generating"
              >
                <Square className="w-4 h-4 fill-current" />
              </button>
            )}

            {/* Send Button (when not streaming and not in voice mode) */}
            {!isLoading && !voiceProps?.isVoiceMode && (
              <button
                onClick={() => handleSendMessage(enableWebSearch)}
                disabled={!inputMessage.trim()}
                className="p-2.5 bg-blue-500 text-white rounded-full hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shadow-md hover:shadow-lg flex-shrink-0"
                title="Send message"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </button>
            )}
          </div>

          {/* New Chat Button */}
          <button
            onClick={onNewChat}
            className="p-2.5 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-colors shadow-md hover:shadow-lg flex-shrink-0"
            title="Start new conversation"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default MessageInput;
