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

const STORAGE_KEY = 'carrie_conversation_history';

const EXAMPLE_PROMPTS = [
  "How many meetings happened in Nov 2025?",
  "Summarize the Nov general meeting",
  "When did the finance breakout start?",
  "What topics were discussed in October marketing breakout?",
  "Did we ever talk about Genie model in our meetings?",
  "What was the last HR breakout meeting about?",
  "Did we talk about prompt quality and context?",
  "when was the first ever meeting?",
  "How can organizations use claude code?",
  "Did we ever talk about RAG?",
];

const getRandomPrompts = (count: number): string[] => {
  const shuffled = [...EXAMPLE_PROMPTS].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
};

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
  const [displayedPrompts, setDisplayedPrompts] = useState<string[]>(() => getRandomPrompts(2));
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
    setDisplayedPrompts(getRandomPrompts(2));
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

        {/* Example Prompts - shown above input when chat is empty */}
        {messages.length === 0 && !isLoading && (
          <div className="px-4 pb-2">
            <div className="mx-auto max-w-6xl flex gap-2 justify-center">
              {displayedPrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => setInputMessage(prompt)}
                  className="text-sm px-4 py-2 bg-white border border-gray-200 rounded-full hover:border-blue-300 hover:bg-blue-50/50 transition-all text-gray-600 hover:text-gray-800 shadow-sm hover:shadow-md"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

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
