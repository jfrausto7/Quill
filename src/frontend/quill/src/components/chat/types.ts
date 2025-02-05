export interface MessageType {
  type: 'user' | 'bot';
  content: string;
  referencedDocuments?: string[]; // IDs of documents referenced in this message
}