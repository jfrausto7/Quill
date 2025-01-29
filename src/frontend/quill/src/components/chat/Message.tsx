'use client';

import React from 'react';
import { MessageType } from './types';

interface MessageProps {
  message: MessageType;
}

const Message = ({ message }: MessageProps) => {
  return (
    <div
      className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-sm p-3 rounded-lg ${
          message.type === 'user'
            ? 'bg-blue-500 text-white'
            : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white'
        }`}
      >
        {message.content}
      </div>
    </div>
  );
};

export default Message;