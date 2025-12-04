import React, { useState, useEffect } from 'react';
import { Youtube, FileText, LogOut, Upload } from 'lucide-react';
import config from '../../config';
import AuthGate from './AuthGate';
import YouTubeForm from './YouTubeForm';
import PDFForm from './PDFForm';
import JobStatusList, { JobStatus } from './JobStatusList';
import SourcesList, { Source } from './SourcesList';

type TabType = 'youtube' | 'pdf';

const UploadPage: React.FC = () => {
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem('uploadApiKey') || '');
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!sessionStorage.getItem('uploadApiKey'));
  const [activeTab, setActiveTab] = useState<TabType>('youtube');

  const [activeJobs, setActiveJobs] = useState<JobStatus[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [loadingSources, setLoadingSources] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleAuthenticated = (key: string) => {
    setApiKey(key);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    sessionStorage.removeItem('uploadApiKey');
    setApiKey('');
    setIsAuthenticated(false);
  };

  const handleAuthError = () => {
    handleLogout();
  };

  const handleJobStarted = (job: JobStatus) => {
    setActiveJobs(prev => [...prev, job]);
  };

  const dismissJob = (jobId: string) => {
    setActiveJobs(prev => prev.filter(job => job.job_id !== jobId));
  };

  // Fetch sources on mount
  useEffect(() => {
    if (isAuthenticated) {
      fetchSources();
    }
  }, [isAuthenticated]);

  // Poll for job status
  useEffect(() => {
    const processingJobs = activeJobs.filter(job => job.status === 'processing');
    if (processingJobs.length === 0) return;

    const pollInterval = setInterval(async () => {
      const updates = await Promise.all(
        processingJobs.map(async (job) => {
          try {
            const response = await fetch(`${config.apiBaseUrl}/api/upload/status/${job.job_id}`);
            if (response.ok) {
              return await response.json() as JobStatus;
            }
          } catch (err) {
            console.error(`Failed to poll job ${job.job_id}:`, err);
          }
          return null;
        })
      );

      const hasNewlyCompleted = updates.some(
        (update, i) => update && update.status === 'completed' && processingJobs[i].status === 'processing'
      );

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
      const response = await fetch(`${config.apiBaseUrl}/api/upload/sources`);
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

  const deleteSource = async (id: string) => {
    setDeletingId(id);
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/upload/sources/${id}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
      });

      if (response.status === 401) {
        handleLogout();
        return;
      }

      if (response.ok) {
        setSources(sources.filter(s => s.id !== id));
      }
    } catch (err) {
      console.error('Failed to delete source:', err);
    } finally {
      setDeletingId(null);
    }
  };

  if (!isAuthenticated) {
    return <AuthGate onAuthenticated={handleAuthenticated} />;
  }

  return (
    <div className="h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 p-6 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="text-center mb-6 flex-shrink-0">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
          <Upload className="w-8 h-8 text-blue-600" />
        </div>
        <h1 className="text-3xl font-bold text-gray-800">Content Upload</h1>
        <p className="text-gray-600 mt-2">Add content to the knowledge base</p>
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
        {/* Left Column - Upload Form & Jobs */}
        <div className="flex flex-col overflow-y-auto">
          {/* Tab Buttons */}
          <div className="bg-white rounded-2xl shadow-xl p-6 mb-6">
            <div className="flex gap-2 mb-6">
              <button
                onClick={() => setActiveTab('youtube')}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium transition-colors ${
                  activeTab === 'youtube'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <Youtube className="w-5 h-5" />
                YouTube
              </button>
              <button
                onClick={() => setActiveTab('pdf')}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium transition-colors ${
                  activeTab === 'pdf'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <FileText className="w-5 h-5" />
                PDF Slides
              </button>
            </div>

            {/* Form based on active tab */}
            {activeTab === 'youtube' ? (
              <YouTubeForm
                apiKey={apiKey}
                onJobStarted={handleJobStarted}
                onAuthError={handleAuthError}
              />
            ) : (
              <PDFForm
                apiKey={apiKey}
                onJobStarted={handleJobStarted}
                onAuthError={handleAuthError}
              />
            )}
          </div>

          {/* Active Jobs */}
          <JobStatusList jobs={activeJobs} onDismiss={dismissJob} />
        </div>

        {/* Right Column - Sources List */}
        <SourcesList
          sources={sources}
          loading={loadingSources}
          deletingId={deletingId}
          onRefresh={fetchSources}
          onDelete={deleteSource}
        />
      </div>
    </div>
  );
};

export default UploadPage;
