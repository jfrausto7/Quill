'use client';

import React, { useState } from 'react';
import { useDocuments } from '@/hooks/useDocuments';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import { MessageType } from './types';

interface ChatViewProps {
  onBack: () => void;
  initialMessages?: MessageType[];
}

const ChatView = ({ onBack, initialMessages = [] }: ChatViewProps) => {
  const [messages, setMessages] = useState<MessageType[]>(initialMessages);
  const { documents } = useDocuments();

  const handleSendMessage = (messageText: string) => {
    const newMessages: MessageType[] = [
      ...messages,
      { type: 'user', content: messageText },
      { 
        type: 'bot', 
        content: `I'll help you with that. I can see ${documents.length} documents in your storage. Would you like me to proceed?`
      }
    ];
    
    setMessages(newMessages);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]"> {/* Subtract header height */}
      {/* Chat Header */}
      <div className="shrink-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 flex justify-between items-center">
        <button
          onClick={onBack}
          className="text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100"
        >
          ← Back
        </button>
        <h1 className="font-semibold text-gray-900 dark:text-white">Form Assistant</h1>
        <div className="w-8" />
      </div>

      {/* Chat container */}
      <div className="flex flex-col flex-1 min-h-0"> {/* min-h-0 is crucial here */}
        <ChatMessages messages={messages} />
        <ChatInput onSendMessage={handleSendMessage} />
      </div>
    </div>
  );
};

export default ChatView;