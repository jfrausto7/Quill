'use client';

import React, { useState } from 'react';
import { FileText, Trash2, Download, Loader2, Eye } from 'lucide-react';
import PreviewModal from './PreviewModal';

interface DocumentCardProps {
  document: {
    _id: string;
    name: string;
    type: string;
    metadata: {
      size: number;
      type: string;
      lastModified: string;
    };
  };
  onDocumentDeleted: () => void;
}

const DocumentCard = ({ document: doc, onDocumentDeleted }: DocumentCardProps) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      setIsDeleting(true);
      const response = await fetch(`/api/documents?id=${doc._id}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete document');

      onDocumentDeleted();
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Failed to delete document');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDownload = async () => {
    try {
      setIsDownloading(true);
      const response = await fetch(`/api/documents?id=${doc._id}&download=true`);
      
      if (!response.ok) throw new Error('Failed to download document');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = doc.name;
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading document:', error);
      alert('Failed to download document');
    } finally {
      setIsDownloading(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else return (bytes / 1048576).toFixed(1) + ' MB';
  };

  return (
    <>
      <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
        <div 
          className="flex items-center flex-1 cursor-pointer hover:opacity-80"
          onClick={() => setIsPreviewOpen(true)}
        >
          <FileText className="mr-3 text-gray-500 dark:text-gray-400 flex-shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="font-medium text-gray-900 dark:text-white truncate">{doc.name}</p>
            <div className="flex items-center text-sm text-gray-500 dark:text-gray-400 space-x-2">
              <span>{doc.type}</span>
              <span>•</span>
              <span>{formatSize(doc.metadata.size)}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2 ml-4">
          <button
            onClick={() => setIsPreviewOpen(true)}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 
              dark:hover:text-gray-300 transition-colors p-1 rounded-lg"
            aria-label="Preview document"
          >
            <Eye className="h-5 w-5" />
          </button>
          <button
            onClick={handleDownload}
            disabled={isDownloading}
            className={`text-blue-500 hover:text-blue-600 dark:text-blue-400 
              dark:hover:text-blue-300 transition-colors p-1 rounded-lg
              ${isDownloading ? 'opacity-50 cursor-not-allowed' : ''}`}
            aria-label="Download document"
          >
            {isDownloading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Download className="h-5 w-5" />
            )}
          </button>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className={`text-red-500 hover:text-red-600 dark:text-red-400 
              dark:hover:text-red-300 transition-colors p-1 rounded-lg
              ${isDeleting ? 'opacity-50 cursor-not-allowed' : ''}`}
            aria-label="Delete document"
          >
            {isDeleting ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Trash2 className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      <PreviewModal
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        documentId={doc._id}
        documentName={doc.name}
        documentType={doc.metadata.type}
      />
    </>
  );
};

export default DocumentCard;