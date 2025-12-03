import React, { useRef, useEffect } from 'react';
import { ChatMessage } from '../../types/chat';
import { Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import YouTubeThumbnail from './YouTubeThumbnail';

interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

/**
 * Parse a YouTube URL and extract video ID and timestamp
 */
const parseYouTubeUrl = (url: string): { videoId: string; timestamp?: number } | null => {
  try {
    const urlObj = new URL(url);
    let videoId: string | null = null;
    let timestamp: number | undefined;

    // Handle youtube.com/watch?v=VIDEO_ID
    if (urlObj.hostname.includes('youtube.com')) {
      videoId = urlObj.searchParams.get('v');
      const t = urlObj.searchParams.get('t');
      if (t) {
        // Handle formats: "123", "123s", "2m30s", "1h2m30s"
        const match = t.match(/^(\d+)s?$/);
        if (match) {
          timestamp = parseInt(match[1], 10);
        }
      }
    }
    // Handle youtu.be/VIDEO_ID
    else if (urlObj.hostname === 'youtu.be') {
      videoId = urlObj.pathname.slice(1);
      const t = urlObj.searchParams.get('t');
      if (t) {
        const match = t.match(/^(\d+)s?$/);
        if (match) {
          timestamp = parseInt(match[1], 10);
        }
      }
    }

    if (videoId) {
      return { videoId, timestamp };
    }
  } catch {
    // Invalid URL
  }
  return null;
};

/**
 * Extract all YouTube URLs from message content
 */
const extractYouTubeUrls = (content: string): Array<{ url: string; videoId: string; timestamp?: number }> => {
  const urlRegex = /https?:\/\/(?:www\.)?(?:youtube\.com\/watch\?[^\s)]+|youtu\.be\/[^\s)]+)/g;
  const matches = content.match(urlRegex) || [];

  const results: Array<{ url: string; videoId: string; timestamp?: number }> = [];
  const seenVideoIds = new Set<string>();

  for (const url of matches) {
    const parsed = parseYouTubeUrl(url);
    if (parsed && !seenVideoIds.has(parsed.videoId)) {
      seenVideoIds.add(parsed.videoId);
      results.push({ url, ...parsed });
    }
  }

  return results;
};

/**
 * Component for rendering the list of messages
 */
const MessageList: React.FC<MessageListProps> = ({ messages, isLoading }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="p-6 pb-4 w-full max-w-6xl mx-auto">
      {messages.length === 0 && !isLoading ? (
        <div className="flex flex-col items-center justify-center h-full text-center py-12">
          <Bot className="w-16 h-16 text-gray-300 mb-4" />
          <h2 className="text-2xl font-semibold text-gray-700 mb-2">
            Welcome to willAIam
          </h2>
          <p className="text-gray-500 max-w-md">
            Ask questions about Birmingham AI community meeting notes, slide summaries, and transcripts.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {messages.map((message) => (
            <div key={message.id} className={`flex items-start gap-3 ${
              message.type === 'user' ? 'flex-row-reverse' : 'flex-row'
            }`}>
              {/* Avatar */}
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                message.type === 'user' ? 'bg-blue-500' : 'bg-purple-500'
              }`}>
                {message.type === 'user' ? (
                  <User className="w-5 h-5 text-white" />
                ) : (
                  <Bot className="w-5 h-5 text-white" />
                )}
              </div>

              {/* Message Bubble */}
              <div className={`flex-1 min-w-0 max-w-[75%] ${
                message.type === 'user' ? 'flex justify-end' : 'flex justify-start'
              }`}>
                <div className="flex flex-col gap-3">
                  <div className={`rounded-2xl px-4 py-3 ${
                    message.type === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}>
                    {message.type === 'user' ? (
                      <div className="whitespace-pre-wrap break-words">
                        {message.content}
                      </div>
                    ) : (
                      <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-900 prose-strong:text-gray-900 prose-code:text-gray-900">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>

                  {/* YouTube Thumbnails - shown after assistant messages */}
                  {message.type === 'assistant' && (() => {
                    const ytUrls = extractYouTubeUrls(message.content);
                    if (ytUrls.length === 0) return null;
                    return (
                      <div className="flex flex-wrap gap-2">
                        {ytUrls.map((yt, idx) => (
                          <YouTubeThumbnail
                            key={`${yt.videoId}-${idx}`}
                            videoId={yt.videoId}
                            timestamp={yt.timestamp}
                            url={yt.url}
                          />
                        ))}
                      </div>
                    );
                  })()}
                </div>
              </div>
            </div>
          ))}

          {/* Loading Indicator - only show if loading and last message is not assistant (i.e., waiting for first chunk) */}
          {isLoading && messages.length > 0 && messages[messages.length - 1].type !== 'assistant' && (
            <div className="flex items-start gap-3 flex-row">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="bg-gray-100 rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  );
};

export default MessageList;
