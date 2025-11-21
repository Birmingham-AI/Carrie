import { useState } from 'react';
import ChatContainer from './components/chat/ChatContainer';
import ErrorBoundary from './components/error/ErrorBoundary';

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [selectedModel] = useState('gpt-4o-mini'); // Default model

  return (
    <ErrorBoundary context="Application">
      <div className="h-screen w-screen overflow-hidden bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
        {/* Animated background overlay */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,rgba(120,119,198,0.1),rgba(255,255,255,0))]"></div>

        {/* Content */}
        <div className="relative z-10 h-full">
          <ChatContainer
            isSidebarOpen={isSidebarOpen}
            setIsSidebarOpen={setIsSidebarOpen}
            selectedModel={selectedModel}
          />
        </div>
      </div>
    </ErrorBoundary>
  );
}

export default App;
