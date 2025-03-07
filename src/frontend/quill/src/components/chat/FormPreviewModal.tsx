'use client';

import React from 'react';
import { Download, X, Maximize2, Minimize2 } from 'lucide-react';

interface FormPreviewModalProps {
  isOpen: boolean;
  filePath?: string;
  fileName?: string;
  onClose: () => void;
}

const FormPreviewModal: React.FC<FormPreviewModalProps> = ({
  isOpen,
  filePath,
  fileName,
  onClose
}) => {
  const [isFullscreen, setIsFullscreen] = React.useState(false);

  if (!isOpen || !filePath) return null;

  // Extract only the filename portion to display to user
  const displayFileName = fileName || filePath.split('/').pop() || 'Filled Form';
  
  // Create download URL
  const downloadUrl = `/api/download?path=${encodeURIComponent(filePath)}`;
  
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-xl p-4 flex flex-col ${
        isFullscreen 
          ? 'w-[95vw] h-[95vh] max-w-none' 
          : 'w-11/12 max-w-6xl h-[85vh]'
      }`}>
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white truncate max-w-md">
            {displayFileName}
          </h2>
          <div className="flex space-x-2">
            <button
              onClick={toggleFullscreen}
              className="p-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
              aria-label={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </button>
            <a
              href={downloadUrl}
              download={displayFileName}
              className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              <span>Download</span>
            </a>
            <button
              onClick={onClose}
              className="p-2 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors flex items-center gap-2"
            >
              <X className="h-4 w-4" />
              <span>Close</span>
            </button>
          </div>
        </div>
        
        {/* Document Preview */}
        <div className="flex-1 overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg">
          <iframe 
            src={`/api/preview?path=${encodeURIComponent(filePath)}`}
            className="w-full h-full"
            title="Form Preview"
            style={{ 
              /* Remove default iframe borders and padding */
              border: 'none',
              display: 'block',
              /* Scale content to fit if needed */
              transformOrigin: 'top left',
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default FormPreviewModal;