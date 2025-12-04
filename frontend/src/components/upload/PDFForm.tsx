import React, { useState, useRef } from 'react';
import { Upload, Loader2, XCircle, FileText } from 'lucide-react';
import config from '../../config';

interface PDFFormProps {
  apiKey: string;
  onJobStarted: (job: { job_id: string; status: string; message: string; source_id?: string }) => void;
  onAuthError: () => void;
}

const PDFForm: React.FC<PDFFormProps> = ({ apiKey, onJobStarted, onAuthError }) => {
  const [file, setFile] = useState<File | null>(null);
  const [sessionInfo, setSessionInfo] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
        setError('Please select a PDF file');
        setFile(null);
        return;
      }
      setError(null);
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_info', sessionInfo);

      const response = await fetch(`${config.apiBaseUrl}/api/upload/pdf`, {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey,
        },
        body: formData,
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
        source_id: file.name,
      });

      setFile(null);
      setSessionInfo('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          PDF File *
        </label>
        <div
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
            file ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
          />
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileText className="w-8 h-8 text-blue-600" />
              <div className="text-left">
                <p className="font-medium text-gray-800">{file.name}</p>
                <p className="text-sm text-gray-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
          ) : (
            <>
              <Upload className="w-10 h-10 text-gray-400 mx-auto mb-2" />
              <p className="text-gray-600">Click to select a PDF file</p>
              <p className="text-sm text-gray-400 mt-1">or drag and drop</p>
            </>
          )}
        </div>
      </div>

      <div className="mb-4">
        <label htmlFor="pdfSessionInfo" className="block text-sm font-medium text-gray-700 mb-1">
          Session Info *
        </label>
        <input
          type="text"
          id="pdfSessionInfo"
          value={sessionInfo}
          onChange={(e) => setSessionInfo(e.target.value)}
          placeholder="e.g., Nov 2024 Birmingham AI Meetup"
          className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
          required
        />
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
          <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting || !file || !sessionInfo}
        className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Uploading...
          </>
        ) : (
          <>
            <Upload className="w-5 h-5" />
            Process PDF
          </>
        )}
      </button>
    </form>
  );
};

export default PDFForm;
