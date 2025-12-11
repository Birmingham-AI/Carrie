import React, { useState, useRef, useEffect, useCallback } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { ChatMessage, VoiceInputProps } from '../../types/chat';
import apiService from '../../services/ApiService';
import { useVoice } from '../../hooks/useVoice';

interface ChatContainerProps {
  isSidebarOpen?: boolean;
  setIsSidebarOpen?: (open: boolean) => void;
  selectedModel?: string;
}

const STORAGE_KEY = 'willaim_conversation_history';

/**
 * Main container component for the chat interface
 * Conversation history persisted in localStorage
 */
const ChatContainer: React.FC<ChatContainerProps> = ({ selectedModel = 'gpt-4o-mini' }) => {
  // Load messages from localStorage on mount
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  });
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Voice message handlers
  const handleVoiceUserMessage = useCallback((content: string) => {
    if (!content.trim()) return;
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content,
      timestamp: new Date().toISOString(),
      isVoice: true
    };
    setMessages(prev => [...prev, userMessage]);
  }, []);

  const handleVoiceAssistantMessage = useCallback((content: string) => {
    if (!content.trim()) return;
    const assistantMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'assistant',
      content,
      timestamp: new Date().toISOString(),
      isVoice: true
    };
    setMessages(prev => [...prev, assistantMessage]);
  }, []);

  // Initialize voice hook with callbacks
  const voice = useVoice(handleVoiceUserMessage, handleVoiceAssistantMessage);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  const handleSendMessage = async (enableWebSearch: boolean = true) => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = inputMessage;
    setInputMessage('');
    setIsLoading(true);

    // Create assistant message ID
    const assistantMessageId = (Date.now() + 1).toString();

    // Build conversation history for backend (excluding the current user message)
    const conversationHistory = messages.map(msg => ({
      role: msg.type === 'user' ? 'user' : 'assistant',
      content: msg.content
    }));

    try {
      // Use streaming API
      abortControllerRef.current = apiService.streamMessage(
        currentInput,
        enableWebSearch,
        conversationHistory,
        // On chunk received
        (chunk: string) => {
          setMessages(prev => {
            // Check if assistant message exists
            const hasAssistantMsg = prev.some(msg => msg.id === assistantMessageId);

            if (!hasAssistantMsg) {
              // Create the assistant message on first chunk
              return [...prev, {
                id: assistantMessageId,
                type: 'assistant' as const,
                content: chunk,
                timestamp: new Date().toISOString()
              }];
            } else {
              // Update existing assistant message
              return prev.map(msg =>
                msg.id === assistantMessageId
                  ? { ...msg, content: msg.content + chunk }
                  : msg
              );
            }
          });
        },
        // On complete
        () => {
          setIsLoading(false);
          abortControllerRef.current = null;
        },
        // On error
        (error: Error) => {
          console.error('Streaming error:', error);
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantMessageId
                ? { ...msg, content: 'Sorry, there was an error processing your request.' }
                : msg
            )
          );
          setIsLoading(false);
          abortControllerRef.current = null;
        },
        // On trace ID received
        (traceId: string) => {
          setMessages(prev => {
            const hasAssistantMsg = prev.some(msg => msg.id === assistantMessageId);
            if (!hasAssistantMsg) {
              // Create assistant message with trace ID (content will be added later)
              return [...prev, {
                id: assistantMessageId,
                type: 'assistant' as const,
                content: '',
                timestamp: new Date().toISOString(),
                traceId
              }];
            } else {
              // Update existing message with trace ID
              return prev.map(msg =>
                msg.id === assistantMessageId
                  ? { ...msg, traceId }
                  : msg
              );
            }
          });
        }
      );
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessageId
            ? { ...msg, content: 'Sorry, there was an error processing your request.' }
            : msg
        )
      );
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    // Cancel any ongoing streaming
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setMessages([]);
    setInputMessage('');
    setIsLoading(false);
    // Clear conversation history from localStorage
    localStorage.removeItem(STORAGE_KEY);
  };

  const cancelStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  };

  return (
    <div className="flex h-full bg-white/70 backdrop-blur-sm overflow-hidden w-full max-w-full">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <MessageList
            messages={messages}
            isLoading={isLoading}
          />
        </div>

        {/* Input */}
        <MessageInput
          inputMessage={inputMessage}
          setInputMessage={setInputMessage}
          handleSendMessage={handleSendMessage}
          isLoading={isLoading}
          cancelStreaming={cancelStreaming}
          onNewChat={handleNewChat}
          voiceProps={{
            isSupported: voice.isSupported,
            isVoiceMode: voice.isVoiceMode,
            isConnecting: voice.isConnecting,
            onToggleVoiceMode: voice.toggleVoiceMode
          } as VoiceInputProps}
        />
      </div>
    </div>
  );
};

export default ChatContainer;
