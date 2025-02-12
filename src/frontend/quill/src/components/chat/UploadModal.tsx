'use client';

import React from 'react';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

interface UploadModalProps {
  isOpen: boolean;
  status: 'loading' | 'success' | 'error';
  fileName?: string;
  errorMessage?: string;
  onClose: () => void;
}

const UploadModal: React.FC<UploadModalProps> = ({
  isOpen, 
  status, 
  fileName, 
  errorMessage, 
  onClose 
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-sm w-full">
        <div className="flex flex-col items-center space-y-4">
          {status === 'loading' && (
            <Loader2 className="h-12 w-12 animate-spin text-blue-500" />
          )}
          {status === 'success' && (
            <CheckCircle className="h-12 w-12 text-green-500" />
          )}
          {status === 'error' && (
            <XCircle className="h-12 w-12 text-red-500" />
          )}

          <div className="text-center">
            {status === 'loading' && (
              <p className="text-gray-700 dark:text-gray-300">
                Uploading {fileName}...
              </p>
            )}
            {status === 'success' && (
              <p className="text-gray-700 dark:text-gray-300">
                {fileName} uploaded successfully
              </p>
            )}
            {status === 'error' && (
              <p className="text-red-600">
                {errorMessage || 'Upload failed'}
              </p>
            )}
          </div>

          {(status === 'success' || status === 'error') && (
            <button
              onClick={onClose}
              className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default UploadModal;