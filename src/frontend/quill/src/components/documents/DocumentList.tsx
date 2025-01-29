'use client';

import React from 'react';
import DocumentCard from './DocumentCard';
import { useDocuments } from '@/hooks/useDocuments';

const DocumentList = () => {
  const { documents } = useDocuments();

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
      <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">Your Documents</h2>
      <div className="space-y-4">
        {documents.map((doc) => (
          <DocumentCard key={doc.id} document={doc} />
        ))}
        {documents.length === 0 && (
          <p className="text-gray-500 dark:text-gray-400 text-center py-4">
            No documents uploaded yet
          </p>
        )}
      </div>
    </div>
  );
};

export default DocumentList;