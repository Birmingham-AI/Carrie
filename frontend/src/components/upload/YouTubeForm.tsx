import React, { useState } from 'react';
import { Upload, Loader2, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import config from '../../config';

interface YouTubeFormProps {
  apiKey: string;
  onJobStarted: (job: { job_id: string; status: string; message: string; source_id?: string }) => void;
  onAuthError: () => void;
}

const YouTubeForm: React.FC<YouTubeFormProps> = ({ apiKey, onJobStarted, onAuthError }) => {
  const [url, setUrl] = useState('');
  const [sessionInfo, setSessionInfo] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [chunkSize, setChunkSize] = useState(1000);
  const [overlap, setOverlap] = useState(1);
  const [language, setLanguage] = useState('en');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch(`${config.apiBaseUrl}/api/upload/youtube`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({
          url,
          session_info: sessionInfo,
          chunk_size: chunkSize,
          overlap,
          language,
        }),
      });

      if (response.status === 401) {
        onAuthError();
        throw new Error('Invalid access key. Please re-enter your key.');
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to start upload');
      }

      const data = await response.json();
      onJobStarted({
        job_id: data.job_id,
        status: 'processing',
        message: data.message,
        source_id: data.source_id,
      });

      setUrl('');
      setSessionInfo('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="mb-4">
        <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
          YouTube URL *
        </label>
        <input
          type="text"
          id="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
          required
        />
      </div>

      <div className="mb-4">
        <label htmlFor="sessionInfo" className="block text-sm font-medium text-gray-700 mb-1">
          Session Info *
        </label>
        <input
          type="text"
          id="sessionInfo"
          value={sessionInfo}
          onChange={(e) => setSessionInfo(e.target.value)}
          placeholder="e.g., Nov 2024 Birmingham AI Meetup"
          className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
          required
        />
      </div>

      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800 mb-4"
      >
        {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        Advanced Options
      </button>

      {showAdvanced && (
        <div className="bg-gray-50 rounded-xl p-4 mb-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="chunkSize" className="block text-sm font-medium text-gray-700 mb-1">
                Chunk Size (chars)
              </label>
              <input
                type="number"
                id="chunkSize"
                value={chunkSize}
                onChange={(e) => setChunkSize(parseInt(e.target.value) || 1000)}
                min={100}
                max={5000}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>
            <div>
              <label htmlFor="overlap" className="block text-sm font-medium text-gray-700 mb-1">
                Overlap (sentences)
              </label>
              <input
                type="number"
                id="overlap"
                value={overlap}
                onChange={(e) => setOverlap(parseInt(e.target.value) || 1)}
                min={0}
                max={10}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>
          </div>
          <div>
            <label htmlFor="language" className="block text-sm font-medium text-gray-700 mb-1">
              Language Code
            </label>
            <input
              type="text"
              id="language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              placeholder="en"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            />
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
          <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting || !url || !sessionInfo}
        className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Starting...
          </>
        ) : (
          <>
            <Upload className="w-5 h-5" />
            Process Video
          </>
        )}
      </button>
    </form>
  );
};

export default YouTubeForm;
