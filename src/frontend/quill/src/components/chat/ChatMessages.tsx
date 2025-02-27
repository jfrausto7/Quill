'use client';

import React, { useEffect, useRef } from 'react';
import { MessageType } from './types';
import LoadingBubble from './LoadingBubble';

interface ChatMessagesProps {
  messages: MessageType[];
  isLoading?: boolean;
}

const ChatMessages = ({ messages, isLoading = false }: ChatMessagesProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900">
      <div className="p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-sm p-3 rounded-lg ${
                message.type === 'user'
                  ? 'text-lg bg-blue-500 text-white'
                  : 'text-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white'
              }`}
            >
              {message.content}
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