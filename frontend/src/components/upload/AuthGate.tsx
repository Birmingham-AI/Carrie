import React, { useState } from 'react';
import { Loader2, XCircle } from 'lucide-react';
import VulcanMascot, { MascotState } from './VulcanMascot';
import config from '../../config';

interface AuthGateProps {
  onAuthenticated: (apiKey: string) => void;
}

const AuthGate: React.FC<AuthGateProps> = ({ onAuthenticated }) => {
  const [apiKey, setApiKey] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [mascotState, setMascotState] = useState<MascotState>('idle');

  const handleAuthenticate = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setIsAuthenticating(true);
    setMascotState('idle');

    try {
      if (!apiKey.trim()) {
        throw new Error('Please enter an access key');
      }

      const response = await fetch(`${config.apiBaseUrl}/api/upload/verify-key`, {
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

      setMascotState('success');
      sessionStorage.setItem('uploadApiKey', apiKey);

      await new Promise(resolve => setTimeout(resolve, 800));
      onAuthenticated(apiKey);
    } catch (err) {
      setMascotState('error');
      setAuthError(err instanceof Error ? err.message : 'Authentication failed');
      setTimeout(() => setMascotState('idle'), 2000);
    } finally {
      setIsAuthenticating(false);
    }
  };

  const handlePasswordFocus = () => setMascotState('typing');
  const handlePasswordBlur = () => {
    if (mascotState === 'typing') setMascotState('idle');
  };

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
};

export default AuthGate;
