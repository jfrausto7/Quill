'use client';

import React from 'react';
import { FileText, Trash2 } from 'lucide-react';
import { useDocuments } from '@/hooks/useDocuments';
import type { Document } from '@/hooks/useDocuments';

interface DocumentCardProps {
  document: Document;
}

const DocumentCard = ({ document }: DocumentCardProps) => {
  const { removeDocument } = useDocuments();

  return (
    <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
      <div className="flex items-center">
        <FileText className="mr-3 text-gray-500 dark:text-gray-400" />
        <div>
          <p className="font-medium text-gray-900 dark:text-white">{document.name}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">{document.type}</p>
        </div>
      </div>
      <button 
        onClick={() => removeDocument(document.id)}
        className="text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300 transition-colors"
        aria-label="Delete document"
      >
        <Trash2 className="h-5 w-5" />
      </button>
    </div>
  );
};

export default DocumentCard;