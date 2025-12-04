import React from 'react';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

export interface JobStatus {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  message: string;
  source_id?: string;
  chunk_count?: number;
  error?: string;
}

interface JobStatusListProps {
  jobs: JobStatus[];
  onDismiss: (jobId: string) => void;
}

const JobStatusList: React.FC<JobStatusListProps> = ({ jobs, onDismiss }) => {
  if (jobs.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-gray-700">
        Active Jobs ({jobs.filter(j => j.status === 'processing').length} processing)
      </h3>
      {jobs.map((job) => (
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
                    onClick={() => onDismiss(job.job_id)}
                    className="text-gray-400 hover:text-gray-600 p-1"
                    title="Dismiss"
                  >
                    <XCircle className="w-4 h-4" />
                  </button>
                )}
              </div>
              <p className="text-gray-600 text-xs mt-1 truncate">{job.message}</p>
              {job.source_id && (
                <p className="text-gray-500 text-xs mt-1">ID: {job.source_id}</p>
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
  );
};

export default JobStatusList;
