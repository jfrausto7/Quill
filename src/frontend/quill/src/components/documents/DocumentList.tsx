'use client';

import React, { useEffect, useState } from 'react';
import DocumentCard from './DocumentCard';
import { FileText } from 'lucide-react';

interface StoredDocument {
  _id: string;
  name: string;
  type: string;
  metadata: {
    size: number;
    type: string;
    lastModified: string;
  };
}

const DocumentList = () => {
  const [documents, setDocuments] = useState<StoredDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchDocuments = async () => {
    try {
      const response = await fetch('/api/documents');
      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
      <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">Your Documents</h2>
      <div className="space-y-4">
        {isLoading ? (
          <div className="text-center py-4">
            <div className="animate-spin h-8 w-8 mx-auto">
              <FileText className="text-gray-500 dark:text-gray-400" />
            </div>
            <p className="mt-2 text-gray-500 dark:text-gray-400">Loading documents...</p>
          </div>
        ) : documents.length > 0 ? (
          documents.map((doc) => (
            <DocumentCard 
              key={doc._id} 
              document={doc}
              onDocumentDeleted={fetchDocuments}
            />
          ))
        ) : (
          <p className="text-gray-500 dark:text-gray-400 text-center py-4">
            No documents uploaded yet
          </p>
        )}
      </div>
    </div>
  );
};

export default DocumentList;