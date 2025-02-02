'use client';

import React, { useState, useCallback } from 'react';
import { MessageSquare } from 'lucide-react';
import Header from './layout/Header';
import UploadSection from './documents/UploadSection';
import DocumentList from './documents/DocumentList';
import ChatView from './chat/ChatView';

const DocumentAssistant = () => {
  const [view, setView] = useState<'landing' | 'chat'>('landing');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleStartChat = () => {
    setView('chat');
  };

  const handleNavigateHome = () => {
    setView('landing');
  };

  // Function to trigger document list refresh
  const refreshDocuments = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  const LandingView = () => (
    <div className="max-w-4xl mx-auto p-6">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4 text-gray-900 dark:text-white">Document Assistant</h1>
        <p className="text-lg text-gray-600 dark:text-gray-300">
          Store your documents securely and let AI help you fill out forms
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-12">
        <UploadSection onUploadComplete={refreshDocuments} />
        
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">Start Filling Forms</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            Ready to fill out a form? Our AI assistant will help you using information from your stored documents.
          </p>
          <button
            onClick={handleStartChat}
            className="bg-green-500 text-white px-6 py-3 rounded-lg flex items-center justify-center w-full hover:bg-green-600 transition-colors"
          >
            <MessageSquare className="mr-2" />
            Start Chat Assistant
          </button>
        </div>
      </div>

      <DocumentList key={refreshTrigger} />
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col bg-gray-100 dark:bg-gray-900">
      <Header onLogoClick={handleNavigateHome} />
      {view === 'landing' ? (
        <LandingView />
      ) : (
        <ChatView 
          onBack={handleNavigateHome}
          initialMessages={[{
            type: 'bot',
            content: "Hello! I can help you fill out forms using information from your stored documents. What form would you like to work on today?"
          }]}
        />
      )}
    </div>
  );
};

export default DocumentAssistant;