import React, { useState, useEffect } from 'react';
import { Upload, Loader2, CheckCircle, XCircle, Youtube, ChevronDown, ChevronUp, RefreshCw, Trash2, LogOut } from 'lucide-react';
import config from '../../config';

// Chibi Vulcan Mascot Component - Birmingham's Iconic Statue
type MascotState = 'idle' | 'typing' | 'error' | 'success';

const VulcanMascot: React.FC<{ state: MascotState }> = ({ state }) => {
  const isTyping = state === 'typing';
  const isError = state === 'error';
  const isSuccess = state === 'success';

  // Bronze/iron color for the statue
  const bronzeMain = '#CD7F32';
  const bronzeDark = '#8B5A2B';
  const bronzeLight = '#DAA520';

  return (
    <div className={`relative w-40 h-48 ${isError ? 'animate-shake' : ''} ${isSuccess ? 'animate-bounce' : ''}`}>
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-5px); }
        }
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-4px); }
          75% { transform: translateX(4px); }
        }
        @keyframes torch-flicker {
          0%, 100% { opacity: 1; transform: scale(1) translateY(0); }
          50% { opacity: 0.9; transform: scale(1.05) translateY(-1px); }
        }
        @keyframes sparkle {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        .animate-float { animation: float 3s ease-in-out infinite; }
        .animate-shake { animation: shake 0.5s ease-in-out; }
        .animate-sparkle { animation: sparkle 0.3s ease-in-out infinite; }
        .torch-flame { animation: torch-flicker 0.4s ease-in-out infinite; }
      `}</style>

      <svg
        viewBox="-5 -15 135 175"
        className={`w-full h-full ${state === 'idle' ? 'animate-float' : ''}`}
      >
        {/* Stone Pedestal */}
        <rect x="25" y="135" width="70" height="12" rx="2" fill="#6B7280" />
        <rect x="30" y="128" width="60" height="10" rx="2" fill="#9CA3AF" />
        <rect x="35" y="122" width="50" height="8" rx="1" fill="#78716C" />

        {/* Legs - strong stance */}
        <path d="M42 100 L38 122 L50 122 L52 100" fill={bronzeMain} />
        <path d="M68 100 L66 122 L78 122 L82 100" fill={bronzeMain} />
        {/* Leg shading */}
        <path d="M44 105 L44 118" stroke={bronzeDark} strokeWidth="2" />
        <path d="M72 105 L72 118" stroke={bronzeDark} strokeWidth="2" />

        {/* Blacksmith Apron - leather brown */}
        <path
          d="M38 68 L35 105 Q60 112 85 105 L82 68 Q60 72 38 68"
          fill="#5C4033"
        />
        {/* Apron shading/folds */}
        <path d="M50 75 L48 100" stroke="#3D2817" strokeWidth="2" fill="none" />
        <path d="M70 75 L72 100" stroke="#3D2817" strokeWidth="2" fill="none" />
        {/* Apron waist tie */}
        <path d="M38 70 Q60 75 82 70" stroke="#8B4513" strokeWidth="3" fill="none" />

        {/* Muscular Torso - bare chest */}
        <ellipse cx="60" cy="58" rx="25" ry="20" fill={bronzeMain} />
        {/* Chest/pec definition */}
        <path d="M45 52 Q52 58 50 62" stroke={bronzeDark} strokeWidth="2" fill="none" />
        <path d="M75 52 Q68 58 70 62" stroke={bronzeDark} strokeWidth="2" fill="none" />
        {/* Center chest line */}
        <path d="M60 48 L60 65" stroke={bronzeDark} strokeWidth="1" fill="none" />
        {/* Abs hint */}
        <path d="M55 65 Q60 67 65 65" stroke={bronzeDark} strokeWidth="1" fill="none" />

        {/* Shoulders - broad and muscular */}
        <ellipse cx="35" cy="52" rx="12" ry="8" fill={bronzeMain} />
        <ellipse cx="85" cy="52" rx="12" ry="8" fill={bronzeMain} />

        {/* Neck */}
        <rect x="52" y="32" width="16" height="14" rx="3" fill={bronzeMain} />

        {/* Head - more oval/heroic proportions */}
        <ellipse cx="60" cy="22" rx="16" ry="18" fill={bronzeMain} />

        {/* Curly Hair/Helmet - Roman style */}
        <ellipse cx="60" cy="10" rx="14" ry="8" fill={bronzeDark} />
        <path d="M46 12 Q50 6 60 5 Q70 6 74 12" fill={bronzeDark} />
        {/* Hair curls */}
        <circle cx="48" cy="14" r="4" fill={bronzeDark} />
        <circle cx="72" cy="14" r="4" fill={bronzeDark} />
        <circle cx="60" cy="8" r="5" fill={bronzeDark} />
        {/* Forehead line */}
        <path d="M46 18 Q60 15 74 18" stroke={bronzeMain} strokeWidth="2" fill="none" />

        {/* Face */}
        {/* Brow ridge */}
        <path d="M48 20 L54 20" stroke={bronzeDark} strokeWidth="2.5" strokeLinecap="round" />
        <path d="M66 20 L72 20" stroke={bronzeDark} strokeWidth="2.5" strokeLinecap="round" />

        {/* Eyebrows - expressive */}
        <path
          d={isError ? "M49 19 L54 21" : isSuccess ? "M49 18 L54 17" : "M49 19 L54 19"}
          stroke={bronzeDark}
          strokeWidth="2"
          strokeLinecap="round"
          style={{ transition: 'all 0.3s ease' }}
        />
        <path
          d={isError ? "M66 21 L71 19" : isSuccess ? "M66 17 L71 18" : "M66 19 L71 19"}
          stroke={bronzeDark}
          strokeWidth="2"
          strokeLinecap="round"
          style={{ transition: 'all 0.3s ease' }}
        />

        {/* Eyes */}
        <g style={{ transition: 'opacity 0.2s ease' }} opacity={isTyping ? 0 : 1}>
          <ellipse cx="51" cy="24" rx="3.5" ry={isSuccess ? 1.5 : 2.5} fill="#FFF8DC" />
          <circle cx="51" cy="24" r={isSuccess ? 1 : 1.5} fill="#1F2937" />
          <ellipse cx="69" cy="24" rx="3.5" ry={isSuccess ? 1.5 : 2.5} fill="#FFF8DC" />
          <circle cx="69" cy="24" r={isSuccess ? 1 : 1.5} fill="#1F2937" />
        </g>

        {/* Closed eyes (when typing) - peaceful */}
        {isTyping && (
          <g>
            <path d="M48 24 Q51 26 54 24" stroke="#1F2937" strokeWidth="2" fill="none" strokeLinecap="round" />
            <path d="M66 24 Q69 26 72 24" stroke="#1F2937" strokeWidth="2" fill="none" strokeLinecap="round" />
          </g>
        )}

        {/* Nose - strong Roman nose */}
        <path d="M60 24 L58 30 L62 30 Z" fill={bronzeDark} />

        {/* Beard - full and flowing, same bronze color */}
        <path
          d="M44 28
             Q42 32 44 38
             Q48 48 60 50
             Q72 48 76 38
             Q78 32 76 28
             Q72 30 68 32
             L60 33
             L52 32
             Q48 30 44 28"
          fill={bronzeDark}
        />
        {/* Beard texture - wavy lines */}
        <path d="M48 34 Q50 38 48 42" stroke={bronzeMain} strokeWidth="1" fill="none" opacity="0.5" />
        <path d="M56 35 Q58 40 56 46" stroke={bronzeMain} strokeWidth="1" fill="none" opacity="0.5" />
        <path d="M64 35 Q62 40 64 46" stroke={bronzeMain} strokeWidth="1" fill="none" opacity="0.5" />
        <path d="M72 34 Q70 38 72 42" stroke={bronzeMain} strokeWidth="1" fill="none" opacity="0.5" />

        {/* Mustache */}
        <path
          d="M52 30 Q56 32 60 31 Q64 32 68 30"
          stroke={bronzeDark}
          strokeWidth="2.5"
          fill="none"
          strokeLinecap="round"
        />

        {/* Mouth - hidden by mustache/beard, just a hint */}
        <path
          d={isError ? "M56 33 Q60 32 64 33" : isSuccess ? "M55 33 Q60 35 65 33" : "M56 33 Q60 34 64 33"}
          stroke="#8B4513"
          strokeWidth="1"
          fill="none"
          style={{ transition: 'all 0.3s ease' }}
        />

        {/* Left Arm */}
        <g>
          <path
            d={isTyping
              ? "M35 52 L30 40 L45 28" // Arm up covering left side of face
              : "M35 52 L25 70 L28 88" // Arm down at side
            }
            stroke={bronzeMain}
            strokeWidth="11"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            style={{ transition: 'd 0.4s ease-in-out' }}
          />
          {/* Left hand */}
          <ellipse
            cx={isTyping ? 45 : 28}
            cy={isTyping ? 28 : 88}
            rx="7"
            ry="7"
            fill={bronzeMain}
            style={{ transition: 'cx 0.4s ease-in-out, cy 0.4s ease-in-out' }}
          />
        </g>

        {/* Right Arm with Spear */}
        <g>
          <path
            d={isTyping
              ? "M85 52 L90 40 L75 28" // Arm up covering right side of face
              : "M85 52 L98 38 L102 20" // Arm raised holding spear
            }
            stroke={bronzeMain}
            strokeWidth="11"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            style={{ transition: 'd 0.4s ease-in-out' }}
          />
          {/* Right hand */}
          <ellipse
            cx={isTyping ? 75 : 102}
            cy={isTyping ? 28 : 20}
            rx="7"
            ry="7"
            fill={bronzeMain}
            style={{ transition: 'cx 0.4s ease-in-out, cy 0.4s ease-in-out' }}
          />

          {/* Spear - only visible when not typing */}
          <g style={{ opacity: isTyping ? 0 : 1, transition: 'opacity 0.3s ease-in-out' }}>
            {/* Spear shaft */}
            <rect x="100" y="2" width="3" height="22" rx="1" fill="#5C4033" />
            {/* Spear head - triangle */}
            <path d="M101.5 -12 L95 2 L108 2 Z" fill="#78716C" />
            {/* Spear head shine */}
            <path d="M101.5 -8 L101.5 0" stroke="#A8A29E" strokeWidth="1" />
          </g>
        </g>

        {/* Success sparkles */}
        {isSuccess && (
          <g className="animate-sparkle">
            <polygon points="15,30 17,34 21,34 18,37 19,41 15,38 11,41 12,37 9,34 13,34" fill="#FCD34D" />
            <polygon points="110,50 112,54 116,54 113,57 114,61 110,58 106,61 107,57 104,54 108,54" fill="#FCD34D" />
            <polygon points="60,0 61,5 65,5 62,8 63,12 60,10 57,12 58,8 55,5 59,5" fill="#FCD34D" />
          </g>
        )}

        {/* Error sweat drop */}
        {isError && (
          <g>
            <ellipse cx="80" cy="15" rx="3" ry="5" fill="#87CEEB" />
            <ellipse cx="80" cy="13" rx="1.5" ry="2" fill="#B0E0E6" />
          </g>
        )}
      </svg>
    </div>
  );
};

interface JobStatus {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  message: string;
  video_id?: string;
  chunk_count?: number;
  error?: string;
}

interface Source {
  id: string;
  source_id: string;
  session_info: string;
  chunk_count: number;
  processed_at: string;
}

const YouTubeUpload: React.FC = () => {
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem('uploadApiKey') || '');
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!sessionStorage.getItem('uploadApiKey'));
  const [authError, setAuthError] = useState<string | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [mascotState, setMascotState] = useState<MascotState>('idle');

  const [url, setUrl] = useState('');
  const [sessionInfo, setSessionInfo] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [chunkSize, setChunkSize] = useState(1000);
  const [overlap, setOverlap] = useState(1);
  const [language, setLanguage] = useState('en');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeJobs, setActiveJobs] = useState<JobStatus[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [sources, setSources] = useState<Source[]>([]);
  const [loadingSources, setLoadingSources] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const getAuthHeaders = () => ({
    'Content-Type': 'application/json',
    'X-API-Key': apiKey,
  });

  const handleAuthenticate = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setIsAuthenticating(true);
    setMascotState('idle');

    try {
      if (!apiKey.trim()) {
        throw new Error('Please enter an access key');
      }

      // Validate the API key by calling the verify endpoint
      const response = await fetch(`${config.apiBaseUrl}/api/youtube/verify-key`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
      });

      if (response.status === 401) {
        throw new Error('Invalid access key');
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Verification failed');
      }

      // Show success state briefly before transitioning
      setMascotState('success');
      sessionStorage.setItem('uploadApiKey', apiKey);

      // Brief delay to show happy Vulcan
      await new Promise(resolve => setTimeout(resolve, 800));
      setIsAuthenticated(true);
    } catch (err) {
      setMascotState('error');
      setAuthError(err instanceof Error ? err.message : 'Authentication failed');
      // Reset to idle after showing error
      setTimeout(() => setMascotState('idle'), 2000);
    } finally {
      setIsAuthenticating(false);
    }
  };

  const handlePasswordFocus = () => setMascotState('typing');
  const handlePasswordBlur = () => {
    if (mascotState === 'typing') setMascotState('idle');
  };

  const handleLogout = () => {
    sessionStorage.removeItem('uploadApiKey');
    setApiKey('');
    setIsAuthenticated(false);
  };

  // Fetch existing sources on mount
  useEffect(() => {
    fetchSources();
  }, []);

  // Poll for job status when there are processing jobs
  useEffect(() => {
    const processingJobs = activeJobs.filter(job => job.status === 'processing');
    if (processingJobs.length === 0) return;

    const pollInterval = setInterval(async () => {
      const updates = await Promise.all(
        processingJobs.map(async (job) => {
          try {
            const response = await fetch(`${config.apiBaseUrl}/api/youtube/status/${job.job_id}`);
            if (response.ok) {
              return await response.json() as JobStatus;
            }
          } catch (err) {
            console.error(`Failed to poll job ${job.job_id}:`, err);
          }
          return null;
        })
      );

      // Check if any jobs completed
      const hasNewlyCompleted = updates.some(
        (update, i) => update && update.status === 'completed' && processingJobs[i].status === 'processing'
      );

      // Update jobs state with new statuses
      setActiveJobs(prev => prev.map(job => {
        const update = updates.find((u) => u && u.job_id === job.job_id);
        return update || job;
      }));

      if (hasNewlyCompleted) {
        fetchSources();
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [activeJobs]);

  const fetchSources = async () => {
    try {
      setLoadingSources(true);
      const response = await fetch(`${config.apiBaseUrl}/api/youtube/sources`);
      if (response.ok) {
        const data = await response.json();
        setSources(data.sources || []);
      }
    } catch (err) {
      console.error('Failed to fetch sources:', err);
    } finally {
      setLoadingSources(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch(`${config.apiBaseUrl}/api/youtube/upload`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          url,
          session_info: sessionInfo,
          chunk_size: chunkSize,
          overlap,
          language,
        }),
      });

      if (response.status === 401) {
        // Invalid API key, log out
        handleLogout();
        throw new Error('Invalid access key. Please re-enter your key.');
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to start upload');
      }

      const data = await response.json();
      // Add new job to the array instead of replacing
      setActiveJobs(prev => [...prev, {
        job_id: data.job_id,
        status: 'processing',
        message: data.message,
        video_id: data.video_id,
      }]);

      // Clear form on successful submission
      setUrl('');
      setSessionInfo('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  const deleteSource = async (id: string) => {
    if (!confirm('Are you sure you want to delete this video and all its embeddings?')) {
      return;
    }

    setDeletingId(id);
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/youtube/sources/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });

      if (response.status === 401) {
        handleLogout();
        throw new Error('Invalid access key. Please re-enter your key.');
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete source');
      }

      // Remove from local state
      setSources(sources.filter(s => s.id !== id));
    } catch (err) {
      console.error('Failed to delete source:', err);
      alert(err instanceof Error ? err.message : 'Failed to delete source');
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const dismissJob = (jobId: string) => {
    setActiveJobs(prev => prev.filter(job => job.job_id !== jobId));
  };

  // Show authentication gate if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 flex items-center justify-center p-6">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
          <div className="text-center mb-6">
            <div className="flex justify-center mb-4">
              <VulcanMascot state={mascotState} />
            </div>
            <h1 className="text-2xl font-bold text-gray-800">Access Required</h1>
            <p className="text-gray-600 mt-2">Enter your access key to continue</p>
          </div>

          <form onSubmit={handleAuthenticate}>
            <div className="mb-4">
              <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700 mb-1">
                Access Key
              </label>
              <input
                type="password"
                id="apiKey"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                onFocus={handlePasswordFocus}
                onBlur={handlePasswordBlur}
                placeholder="Enter your access key"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                autoFocus
              />
            </div>

            {authError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2">
                <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                <p className="text-red-700 text-sm">{authError}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isAuthenticating || !apiKey.trim()}
              className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {isAuthenticating ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                'Unlock'
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 p-6 overflow-hidden flex flex-col">
      {/* Header - Centered */}
      <div className="text-center mb-6 flex-shrink-0">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
          <Youtube className="w-8 h-8 text-red-600" />
        </div>
        <h1 className="text-3xl font-bold text-gray-800">YouTube Transcription</h1>
        <p className="text-gray-600 mt-2">Add YouTube videos to the knowledge base</p>
        <button
          onClick={handleLogout}
          className="mt-2 text-sm text-gray-500 hover:text-gray-700 inline-flex items-center gap-1"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>

      {/* 2-Column Layout */}
      <div className="flex-1 max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-hidden">
        {/* Left Column - Upload Form & Status */}
        <div className="flex flex-col overflow-y-auto">
          {/* Upload Form */}
          <div className="bg-white rounded-2xl shadow-xl p-6 mb-6">
            <form onSubmit={handleSubmit}>
              {/* URL Input */}
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

              {/* Session Info Input */}
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

              {/* Advanced Options Toggle */}
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800 mb-4"
              >
                {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                Advanced Options
              </button>

              {/* Advanced Options */}
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

              {/* Error Message */}
              {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
                  <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <p className="text-red-700 text-sm">{error}</p>
                </div>
              )}

              {/* Submit Button */}
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
          </div>

          {/* Active Jobs Status */}
          {activeJobs.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-gray-700">
                Active Jobs ({activeJobs.filter(j => j.status === 'processing').length} processing)
              </h3>
              {activeJobs.map((job) => (
                <div
                  key={job.job_id}
                  className={`bg-white rounded-2xl shadow-xl p-4 border-l-4 ${
                    job.status === 'processing' ? 'border-blue-500' :
                    job.status === 'completed' ? 'border-green-500' :
                    'border-red-500'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {job.status === 'processing' && (
                      <Loader2 className="w-5 h-5 text-blue-500 animate-spin flex-shrink-0" />
                    )}
                    {job.status === 'completed' && (
                      <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                    )}
                    {job.status === 'failed' && (
                      <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-gray-800 text-sm">
                          {job.status === 'processing' ? 'Processing...' :
                           job.status === 'completed' ? 'Completed!' :
                           'Failed'}
                        </h4>
                        {job.status !== 'processing' && (
                          <button
                            onClick={() => dismissJob(job.job_id)}
                            className="text-gray-400 hover:text-gray-600 p-1"
                            title="Dismiss"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                      <p className="text-gray-600 text-xs mt-1 truncate">{job.message}</p>
                      {job.video_id && (
                        <p className="text-gray-500 text-xs mt-1">Video: {job.video_id}</p>
                      )}
                      {job.chunk_count !== undefined && (
                        <p className="text-gray-500 text-xs">Chunks: {job.chunk_count}</p>
                      )}
                      {job.error && (
                        <p className="text-red-600 text-xs mt-1">{job.error}</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column - Processed Videos */}
        <div className="bg-white rounded-2xl shadow-xl p-6 flex flex-col h-full overflow-hidden">
          <div className="flex items-center justify-between mb-4 flex-shrink-0">
            <h2 className="text-lg font-semibold text-gray-800">Processed Videos</h2>
            <button
              onClick={fetchSources}
              disabled={loadingSources}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-5 h-5 ${loadingSources ? 'animate-spin' : ''}`} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {loadingSources ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
              </div>
            ) : sources.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Youtube className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No videos processed yet</p>
              </div>
            ) : (
              <div className="space-y-3 pr-2">
                {sources.map((source) => (
                  <div
                    key={source.id}
                    className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
                  >
                    <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Youtube className="w-5 h-5 text-red-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800 truncate">{source.session_info}</p>
                      <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
                        <span>{source.source_id}</span>
                        <span>{source.chunk_count} chunks</span>
                        <span>{formatDate(source.processed_at)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <a
                        href={`https://www.youtube.com/watch?v=${source.source_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                      >
                        View
                      </a>
                      <button
                        onClick={() => deleteSource(source.id)}
                        disabled={deletingId === source.id}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                        title="Delete"
                      >
                        {deletingId === source.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default YouTubeUpload;
