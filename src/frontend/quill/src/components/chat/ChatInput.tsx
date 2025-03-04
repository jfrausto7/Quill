'use client';

import React, { useState, useRef } from 'react';
import { Upload, ClipboardEdit } from 'lucide-react';
import { useDocuments } from '@/hooks/useDocuments';
import UploadModal from './UploadModal';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
  onAgentResponse?: (message: string) => void; // For agent messages
  onSilentUpload?: (fileName: string) => void; // For uploads without triggering LLM
}

const ChatInput = ({ onSendMessage, isLoading = false, onAgentResponse, onSilentUpload }: ChatInputProps) => {
  const [input, setInput] = useState('');
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [uploadError, setUploadError] = useState('');
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [showTooltip1, setShowTooltip1] = useState(false);
  const [showTooltip2, setShowTooltip2] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const blankFileInputRef = useRef<HTMLInputElement>(null);
  const { addDocument } = useDocuments();
  
  // Tooltip timer refs
  const tooltip1Timer = useRef<NodeJS.Timeout | null>(null);
  const tooltip2Timer = useRef<NodeJS.Timeout | null>(null);

  // Helper function to check if a field should be excluded
  const shouldIncludeField = (key: string, value: any): boolean => {
    // Exclude fields that are file paths
    if (typeof value === 'string' && value.includes('vector_db')) return false;
    
    // Exclude technical fields and collection names
    if (key.includes('_')) return false;
    
    // Exclude fields with non-user-friendly values
    if (typeof value === 'string' && (
      value.startsWith('/') || 
      value.includes('\\') || 
      value.includes('/')
    )) return false;
    
    return true;
  };

  const handleMouseEnter = (tooltipNumber: 1 | 2) => {
    const timer = setTimeout(() => {
      if (tooltipNumber === 1) {
        setShowTooltip1(true);
      } else {
        setShowTooltip2(true);
      }
    }, 1000); // 1 second delay
    
    if (tooltipNumber === 1) {
      tooltip1Timer.current = timer;
    } else {
      tooltip2Timer.current = timer;
    }
  };

  const handleMouseLeave = (tooltipNumber: 1 | 2) => {
    if (tooltipNumber === 1) {
      if (tooltip1Timer.current) {
        clearTimeout(tooltip1Timer.current);
      }
      setShowTooltip1(false);
    } else {
      if (tooltip2Timer.current) {
        clearTimeout(tooltip2Timer.current);
      }
      setShowTooltip2(false);
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, isBlank: boolean) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadStatus('loading');
    setUploadedFileName(file.name);
    
    try {
      // Sample form data for blank forms
      const blankFormFields = {
        "Employee social security number": "000-11-2222",
        "Employer identification number": "999-888-777",
        "Wages, tips, other compensation": "64000"
      };
      
      // Create form data
      const formData = new FormData();
      formData.append('file', file);
      formData.append('mode', isBlank ? 'blank' : 'ingest');
      if (isBlank) {
        const jsonString = JSON.stringify(blankFormFields);
        formData.append('jsonString', jsonString);
      }

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
      
      // For normal document uploads (not blank forms)
      if (!isBlank) {
        // Use the silent upload handler if available
        if (onSilentUpload) {
          onSilentUpload(file.name);
        }
        
        // Fetch the user_info.json data after successful upload
        try {
          const userInfoResponse = await fetch('/api/user-info');
          if (userInfoResponse.ok && onAgentResponse) {
            const userInfo = await userInfoResponse.json();
            
            // Create a formatted list of the user info fields, filtering out technical/system fields
            const fieldsList = Object.entries(userInfo)
              .filter(([key, value]) => shouldIncludeField(key, value))
              .map(([field, value]) => `- ${field}: ${value}`)
              .join('\n');
            
            // Create a message from the agent for verification
            const verificationMessage = `I've processed your uploaded document "${file.name}" and extracted the following information. Please verify if these details are correct:\n\n${fieldsList}\n\nWould you like me to make any changes or use this information to fill out forms?`;
            
            // Use a slight delay to ensure the upload modal shows first
            setTimeout(() => {
              onAgentResponse(verificationMessage);
            }, 1000);
          }
        } catch (error) {
          console.error('Error fetching user info:', error);
          
          // Fallback message if we can't get user info
          if (onAgentResponse) {
            setTimeout(() => {
              onAgentResponse(`I've processed your document "${file.name}". Would you like me to help you fill out any forms using the information I extracted?`);
            }, 1000);
          }
        }
      }
    } catch (error) {
      console.error('Full upload error:', error);
      setUploadStatus('error');
      setUploadError(error.message || 'Failed to upload document');
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      if (blankFileInputRef.current) {
        blankFileInputRef.current.value = '';
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
              onChange={(e) => handleFileUpload(e, false)}
              accept=".pdf,.doc,.docx"
              className="hidden"
            />
            <input
              ref={blankFileInputRef}
              type="file"
              onChange={(e) => handleFileUpload(e, true)}
              accept=".pdf,.doc,.docx"
              className="hidden"
            />
            <div className="relative" 
                 onMouseEnter={() => handleMouseEnter(1)} 
                 onMouseLeave={() => handleMouseLeave(1)}>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
                className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200
                         disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Upload document"
              >
                <Upload className="h-5 w-5" />
              </button>
              {showTooltip1 && (
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-1 
                          bg-gray-900 text-white text-sm rounded-md whitespace-nowrap z-10
                          transition-opacity duration-200">
                  Upload document to analyze
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent 
                            border-t-gray-900"></div>
                </div>
              )}
            </div>
            <div className="relative"
                 onMouseEnter={() => handleMouseEnter(2)} 
                 onMouseLeave={() => handleMouseLeave(2)}>
              <button
                type="button"
                onClick={() => blankFileInputRef.current?.click()}
                disabled={isLoading}
                className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200
                         disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Upload and fill blank form"
              >
                <ClipboardEdit className="h-5 w-5" />
              </button>
              {showTooltip2 && (
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-1 
                          bg-gray-900 text-white text-sm rounded-md whitespace-nowrap z-10
                          transition-opacity duration-200">
                  Upload blank form to fill out
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent 
                            border-t-gray-900"></div>
                </div>
              )}
            </div>
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