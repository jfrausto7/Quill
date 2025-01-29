'use client';

import React, { useRef } from 'react';
import { Upload } from 'lucide-react';
import { useDocuments } from '@/hooks/useDocuments';

const UploadSection = () => {
  const { addDocument } = useDocuments();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      addDocument({
        name: file.name,
        type: determineDocumentType(file.name)
      });
      
      // Reset file input
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
      <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">Upload Documents</h2>
      <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center">
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
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
          Supported formats: PDF, DOC, DOCX
        </p>
      </div>
    </div>
  );
};

export default UploadSection;