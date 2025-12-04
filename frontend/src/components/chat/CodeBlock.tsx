import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';

interface CodeBlockProps {
  language?: string;
  children: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ language, children }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group my-3 rounded-lg overflow-hidden border border-gray-200">
      {/* Header with language label and copy button */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-100 border-b border-gray-200">
        <span className="text-xs font-medium text-gray-600">
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code content */}
      <SyntaxHighlighter
        language={language || 'text'}
        style={oneLight}
        customStyle={{
          margin: 0,
          padding: '1rem',
          fontSize: '0.875rem',
          background: '#fafafa',
        }}
        wrapLongLines={true}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
};

export default CodeBlock;
