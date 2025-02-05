'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useDocuments, useDocumentRefresh } from '@/hooks/useDocuments';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import { MessageType } from './types';

interface ChatViewProps {
  onBack: () => void;
  initialMessages?: MessageType[];
}

const ChatView = ({ onBack, initialMessages = [] }: ChatViewProps) => {
  const [messages, setMessages] = useState<MessageType[]>(initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  const { documents } = useDocuments();
  const refreshDocuments = useDocumentRefresh();
  
  // Only refresh documents once when component mounts
  useEffect(() => {
    refreshDocuments();
  }, []); // Empty dependency array, only runs once on mount

  const handleSendMessage = async (messageText: string) => {
    try {
      setIsLoading(true);
      
      // Get current document IDs without refreshing
      const allDocumentIds = documents.map(doc => doc._id);
      
      const updatedMessages = [
        ...messages,
        { 
          type: 'user', 
          content: messageText,
          referencedDocuments: allDocumentIds
        }
      ];
      setMessages(updatedMessages);

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageText,
          documentIds: allDocumentIds
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get response');
      }

      const data = await response.json();
      
      setMessages([
        ...updatedMessages,
        { 
          type: 'bot', 
          content: data.content,
          referencedDocuments: allDocumentIds
        }
      ]);
    } catch (error) {
      console.error('Error in chat:', error);
      setMessages([
        ...messages,
        { type: 'user', content: messageText },
        { 
          type: 'bot', 
          content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}` 
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-none bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 flex justify-between items-center">
        <button
          onClick={onBack}
          className="text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100"
        >
          ← Back
        </button>
        <h1 className="font-semibold text-gray-900 dark:text-white">Form Assistant</h1>
        <div className="w-8" />
      </div>

      <div className="flex flex-col flex-1 overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          <ChatMessages 
            messages={messages} 
            documents={documents}
            isLoading={isLoading}
          />
        </div>
        
        <div className="flex-none">
          <ChatInput 
            onSendMessage={handleSendMessage} 
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
};

export default ChatView;