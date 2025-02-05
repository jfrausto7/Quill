'use client';

import React, { useEffect, useRef } from 'react';
import { MessageType } from './types';
import LoadingBubble from './LoadingBubble';
import { FileText } from 'lucide-react';

interface ChatMessagesProps {
  messages: MessageType[];
  isLoading?: boolean;
  documents: Array<{
    _id: string;
    name: string;
    type: string;
  }>;
}

const ChatMessages = ({ messages, isLoading = false, documents }: ChatMessagesProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Helper function to get document names from IDs
  const getDocumentNames = (docIds?: string[]) => {
    if (!docIds?.length) return null;
    const referencedDocs = documents.filter(doc => docIds.includes(doc._id));
    if (!referencedDocs.length) return null;
    
    return (
      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-1">
          <FileText className="h-3 w-3" />
          <span>Referenced documents:</span>
        </div>
        <ul className="ml-4 list-disc">
          {referencedDocs.map(doc => (
            <li key={doc._id}>{doc.name}</li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900">
      <div className="p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={`${index}-${message.type}`}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-sm p-3 rounded-lg ${
                message.type === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white'
              }`}
            >
              <div>{message.content}</div>
              {message.type === 'bot' && getDocumentNames(message.referencedDocuments)}
            </div>
          </div>
        ))}
        {isLoading && <LoadingBubble />}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ChatMessages;