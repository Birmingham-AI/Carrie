import React, { useState, useRef } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { ChatMessage } from '../../types/chat';
import apiService from '../../services/ApiService';

interface ChatContainerProps {
  isSidebarOpen?: boolean;
  setIsSidebarOpen?: (open: boolean) => void;
  selectedModel?: string;
}

/**
 * Main container component for the chat interface
 * Simple single-session chat with no persistence
 */
const ChatContainer: React.FC<ChatContainerProps> = ({ selectedModel = 'gpt-4o-mini' }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

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

    try {
      // Use streaming API
      abortControllerRef.current = apiService.streamMessage(
        currentInput,
        enableWebSearch,
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
  };

  const cancelStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  };

  return (
    <div className="flex h-full bg-white overflow-hidden w-full max-w-full">
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
        />
      </div>
    </div>
  );
};

export default ChatContainer;
