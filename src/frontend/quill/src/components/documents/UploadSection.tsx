'use client';

import React, { useRef, useState } from 'react';
import { Upload, Loader2 } from 'lucide-react';

interface UploadSectionProps {
  onUploadComplete?: () => void;  // Add this prop
}

const UploadSection = ({ onUploadComplete }: UploadSectionProps) => {
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      
      // Create FormData and send to API
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/documents', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // Notify parent component to refresh document list
      onUploadComplete?.();

    } catch (error) {
      console.error('Upload error:', error);
      alert('Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
      <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">Upload Documents</h2>
      <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center">
        {isUploading ? (
          <div className="flex flex-col items-center">
            <Loader2 className="h-12 w-12 text-gray-400 dark:text-gray-500 mb-4 animate-spin" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Uploading document...
            </p>
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
                disabled={isUploading}
              />
            </label>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              Supported formats: PDF, DOC, DOCX
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default UploadSection;