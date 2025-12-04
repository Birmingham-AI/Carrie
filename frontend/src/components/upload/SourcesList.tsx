import React from 'react';
import { Loader2, RefreshCw, Trash2, Youtube, FileText } from 'lucide-react';

export interface Source {
  id: string;
  source_type: string;
  source_id: string;
  session_info: string;
  chunk_count: number;
  processed_at: string;
}

interface SourcesListProps {
  sources: Source[];
  loading: boolean;
  deletingId: string | null;
  onRefresh: () => void;
  onDelete: (id: string) => void;
}

const SourcesList: React.FC<SourcesListProps> = ({
  sources,
  loading,
  deletingId,
  onRefresh,
  onDelete,
}) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleDelete = (id: string, sourceType: string) => {
    const typeLabel = sourceType === 'youtube' ? 'video' : 'PDF';
    if (!confirm(`Are you sure you want to delete this ${typeLabel} and all its embeddings?`)) {
      return;
    }
    onDelete(id);
  };

  const formatSourceType = (type: string): string => {
    const displayNames: Record<string, string> = {
      youtube: 'YouTube',
      pdf: 'PDF',
    };
    return displayNames[type] ?? type;
  };

  const getSourceIcon = (sourceType: string) => {
    if (sourceType === 'youtube') {
      return (
        <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
          <Youtube className="w-5 h-5 text-red-600" />
        </div>
      );
    }
    return (
      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
        <FileText className="w-5 h-5 text-blue-600" />
      </div>
    );
  };

  const getViewLink = (source: Source) => {
    if (source.source_type === 'youtube') {
      return (
        <a
          href={`https://www.youtube.com/watch?v=${source.source_id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-700 text-sm font-medium"
        >
          View
        </a>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-6 flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h2 className="text-lg font-semibold text-gray-800">Processed Sources</h2>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
          </div>
        ) : sources.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No sources processed yet</p>
          </div>
        ) : (
          <div className="space-y-3 pr-2">
            {sources.map((source) => (
              <div
                key={source.id}
                className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
              >
                {getSourceIcon(source.source_type)}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-800 truncate">{source.session_info}</p>
                  <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
                    <span>{formatSourceType(source.source_type)}</span>
                    <span>{source.chunk_count} chunks</span>
                    <span>{formatDate(source.processed_at)}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {getViewLink(source)}
                  <button
                    onClick={() => handleDelete(source.id, source.source_type)}
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
  );
};

export default SourcesList;
