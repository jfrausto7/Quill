'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

export interface Document {
  _id: string;  // Changed from id to _id to match MongoDB
  name: string;
  type: string;
  metadata?: {
    size: number;
    type: string;
    lastModified: string;
  };
}

interface DocumentContextType {
  documents: Document[];
  addDocument: (document: Omit<Document, '_id'>) => void;
  removeDocument: (id: string) => void;
  refreshDocuments: () => Promise<void>;
}

export const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

export function DocumentProvider({ children }: { children: React.ReactNode }) {
  const [documents, setDocuments] = useState<Document[]>([]);

  const fetchDocuments = async () => {
    try {
      const response = await fetch('/api/documents');
      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }
      const data = await response.json();
      setDocuments(data.documents);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchDocuments();
  }, []);

  const addDocument = async (document: Omit<Document, '_id'>) => {
    try {
      // Note: actual document upload is handled elsewhere
      // This is just to refresh the list after upload
      await fetchDocuments();
    } catch (error) {
      console.error('Error adding document:', error);
    }
  };

  const removeDocument = async (id: string) => {
    try {
      const response = await fetch(`/api/documents?id=${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete document');
      }

      // Refresh documents list after deletion
      await fetchDocuments();
    } catch (error) {
      console.error('Error removing document:', error);
    }
  };

  return (
    <DocumentContext.Provider 
      value={{
        documents,
        addDocument,
        removeDocument,
        refreshDocuments: fetchDocuments
      }}
    >
      {children}
    </DocumentContext.Provider>
  );
}

export function useDocuments() {
  const context = useContext(DocumentContext);
  if (context === undefined) {
    throw new Error('useDocuments must be used within a DocumentProvider');
  }
  return context;
}