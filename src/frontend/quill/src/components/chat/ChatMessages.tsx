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

  // Function to format message content with proper line breaks
  const formatMessage = (content: string) => {
    // Split the content by newlines and map each line to a paragraph
    return content.split('\n').map((line, i) => (
      // For empty lines (just a line break), use a small spacer div
      line.trim() === '' ? (
        <div key={i} className="h-2"></div>
      ) : (
        <p key={i}>{line}</p>
      )
    ));
  };

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900">
      <div className="p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-sm md:max-w-md lg:max-w-lg p-3 rounded-lg ${
                message.type === 'user'
                  ? 'text-lg bg-blue-500 text-white'
                  : 'text-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white'
              }`}
            >
              <div className="whitespace-pre-line">
                {formatMessage(message.content)}
              </div>
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