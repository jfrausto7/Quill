import { useContext } from 'react';
import { DocumentContext, Document } from '@/context/DocumentContext';

export type { Document };

export function useDocuments() {
  const context = useContext(DocumentContext);
  
  if (context === undefined) {
    throw new Error('useDocuments must be used within a DocumentProvider');
  }
  
  return context;
}

// Optional: Add helper functions that use the context
export function useDocumentsByType(type: string) {
  const { documents } = useDocuments();
  return documents.filter(doc => doc.type === type);
}

export function useDocumentById(id: number) {
  const { documents } = useDocuments();
  return documents.find(doc => doc.id === id);
}