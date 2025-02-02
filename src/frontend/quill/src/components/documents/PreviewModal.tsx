'use client';

import React, { useState, useEffect } from 'react';
import { X, Loader2 } from 'lucide-react';

interface PreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentId: string;
  documentName: string;
  documentType: string;
}

const PreviewModal = ({ isOpen, onClose, documentId, documentName, documentType }: PreviewModalProps) => {
  const [content, setContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadContent();
    }
  }, [isOpen, documentId]);

  const loadContent = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await fetch(`/api/documents?id=${documentId}&download=true`);
      
      if (!response.ok) throw new Error('Failed to load document');
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setContent(url);
    } catch (error) {
      console.error('Error loading preview:', error);
      setError('Failed to load preview');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-4xl h-[80vh] flex flex-col relative">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {documentName}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-red-500">
              {error}
            </div>
          ) : (
            <div className="h-full">
              {documentType.includes('pdf') ? (
                <iframe
                  src={content + '#toolbar=0'}
                  className="w-full h-full rounded border border-gray-200 dark:border-gray-700"
                />
              ) : documentType.includes('image') ? (
                <img
                  src={content}
                  alt={documentName}
                  className="max-w-full max-h-full mx-auto"
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  Preview not available for this file type
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PreviewModal;