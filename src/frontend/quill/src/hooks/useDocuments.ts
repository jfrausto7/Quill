import { useDocuments } from '@/context/DocumentContext';
import type { Document } from '@/context/DocumentContext';

export type { Document };
export { useDocuments };

// Helper functions that use the context
export function useDocumentsByType(type: string) {
  const { documents } = useDocuments();
  return documents.filter(doc => doc.type === type);
}

export function useDocumentById(id: string) {  // Changed from number to string
  const { documents } = useDocuments();
  return documents.find(doc => doc._id === id);  // Changed from id to _id
}

// New helper hook to force refresh
export function useDocumentRefresh() {
  const { refreshDocuments } = useDocuments();
  return refreshDocuments;
}