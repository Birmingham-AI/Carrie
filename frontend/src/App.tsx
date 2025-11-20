import { useState } from 'react';
import ChatContainer from './components/chat/ChatContainer';
import ErrorBoundary from './components/error/ErrorBoundary';

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [selectedModel] = useState('gpt-4o-mini'); // Default model

  return (
    <ErrorBoundary context="Application">
      <div className="h-screen w-screen overflow-hidden bg-gray-50">
        <ChatContainer
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
          selectedModel={selectedModel}
        />
      </div>
    </ErrorBoundary>
  );
}

export default App;
