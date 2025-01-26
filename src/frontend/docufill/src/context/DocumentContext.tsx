'use client';

import React, { createContext, useState, ReactNode } from 'react';

// Types for our documents
export interface Document {
  id: number;
  name: string;
  type: string;
}

interface DocumentContextType {
  documents: Document[];
  addDocument: (document: Omit<Document, 'id'>) => void;
  removeDocument: (id: number) => void;
}

// Create the context and export it
export const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

// Create the provider component
export function DocumentProvider({ children }: { children: ReactNode }) {
  const [documents, setDocuments] = useState<Document[]>([
    { id: 1, name: '2023_W2.pdf', type: 'Tax Document' },
    { id: 2, name: 'Lease_Agreement.pdf', type: 'Housing' },
    { id: 3, name: 'Medical_Records.pdf', type: 'Healthcare' }
  ]);

  const addDocument = (document: Omit<Document, 'id'>) => {
    setDocuments(prevDocuments => [
      ...prevDocuments,
      {
        id: prevDocuments.length + 1,
        ...document
      }
    ]);
  };

  const removeDocument = (id: number) => {
    setDocuments(prevDocuments => 
      prevDocuments.filter(doc => doc.id !== id)
    );
  };

  return (
    <DocumentContext.Provider 
      value={{
        documents,
        addDocument,
        removeDocument
      }}
    >
      {children}
    </DocumentContext.Provider>
  );
}