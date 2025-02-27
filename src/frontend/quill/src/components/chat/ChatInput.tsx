'use client';

import React, { useState, useRef } from 'react';
import { Upload, Send } from 'lucide-react';
import { useDocuments } from '@/hooks/useDocuments';
import UploadModal from './UploadModal';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
}

const ChatInput = ({ onSendMessage, isLoading = false }: ChatInputProps) => {
  const [input, setInput] = useState('');
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [uploadError, setUploadError] = useState('');
  const [uploadedFileName, setUploadedFileName] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { addDocument } = useDocuments();

  const determineDocumentType = (fileName: string): string => {
    const lowercaseName = fileName.toLowerCase();
    if (lowercaseName.includes('w2') || lowercaseName.includes('tax')) {
      return 'Tax Document';
    } else if (lowercaseName.includes('lease')) {
      return 'Housing';
    } else if (lowercaseName.includes('medical')) {
      return 'Healthcare';
    }
    return 'Other';
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadStatus('loading');
    setUploadedFileName(file.name);
    
    try {
      // Create form data
      const formData = new FormData();
      formData.append('file', file);
      formData.append('mode', 'ingest');

      // Upload and process the file
      const response = await fetch('/api/rag', {
        method: 'POST',
        body: formData,
      });

      const responseData = await response.json();

      if (!response.ok) {
        throw new Error(responseData.error || 'Failed to process document');
      }

      // Add to document list
      addDocument({
        name: file.name,
        type: determineDocumentType(file.name),
        id: Date.now(),
      });

      setUploadStatus('success');
    } catch (error) {
      console.error('Full upload error:', error);
      setUploadStatus('error');
      setUploadError(error.message || 'Failed to upload document');
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const closeModal = () => {
    setUploadStatus('idle');
  };

  return (
    <>
      <UploadModal
        isOpen={uploadStatus !== 'idle'}
        status={uploadStatus === 'loading' ? 'loading' : 
                uploadStatus === 'success' ? 'success' : 'error'}
        fileName={uploadedFileName}
        errorMessage={uploadError}
        onClose={closeModal}
      />
      <div className="shrink-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <form onSubmit={handleSubmit} className="p-4">
          <div className="flex items-center space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe the form you need help with..."
              disabled={isLoading}
              className="text-lg flex-1 p-2 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 
                       bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                       disabled:opacity-50"
            />
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileUpload}
              accept=".pdf,.doc,.docx"
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Upload className="h-5 w-5" />
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="text-lg bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed
                       flex items-center justify-center min-w-[80px]"
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </>
  );
};

export default ChatInput;