'use client';

import React, { useRef, useState } from 'react';
import { Upload, Loader2 } from 'lucide-react';
import { useDocuments } from '@/hooks/useDocuments';

const UploadSection = () => {
  const { addDocument } = useDocuments();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string>('');

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadStatus('');
    
    try {
      // Create form data
      const formData = new FormData();
      formData.append('file', file);
      formData.append('mode', 'ingest');

      console.log('Uploading file:', file.name);

      // Upload and process the file
      const response = await fetch('/api/rag', {
        method: 'POST',
        body: formData,
      });

      // Log the response details
      console.log('Response status:', response.status);
      const responseData = await response.json();
      console.log('Response data:', responseData);

      if (!response.ok) {
        throw new Error(responseData.error || 'Failed to process document');
      }

      // Add to document list
      addDocument({
        name: file.name,
        type: determineDocumentType(file.name),
        id: Date.now(), // Adding an id since your interface requires it
      });

      setUploadStatus('Document uploaded successfully');
    } catch (error) {
      console.error('Full upload error:', error);
      setUploadStatus(error.message || 'Failed to upload document');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

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

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-semibold mb-4 text-gray-900 dark:text-white">Upload Documents</h2>
      <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center">
        {isUploading ? (
          <div className="flex flex-col items-center">
            <Loader2 className="h-12 w-12 animate-spin text-gray-400 dark:text-gray-500 mb-4" />
            <p className="text-md text-gray-500 dark:text-gray-400">Processing document...</p>
          </div>
        ) : (
          <>
            <Upload className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-4" />
            <label className="block">
              <span className="bg-blue-500 text-white px-4 py-2 rounded-lg cursor-pointer hover:bg-blue-600 transition-colors inline-block">
                Choose Files
              </span>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileUpload}
                accept=".pdf,.doc,.docx"
              />
            </label>
            <p className="text-md text-gray-500 dark:text-gray-400 mt-2">
              Supported formats: PDF, DOC, DOCX
            </p>
          </>
        )}
        {uploadStatus && (
          <p className={`mt-4 text-md ${uploadStatus.includes('Failed') ? 'text-red-500' : 'text-green-500'}`}>
            {uploadStatus}
          </p>
        )}
      </div>
    </div>
  );
};

export default UploadSection;