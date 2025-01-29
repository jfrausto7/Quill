'use client';

import React, { createContext, useContext } from 'react';
import { ChatService } from '@/services/chat/ChatService';
import { R1ChatService } from '@/services/chat/R1ChatService';

interface ChatContextType {
  chatService: ChatService;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

// Initialize R1ChatService as the default service
const defaultChatService = new R1ChatService();

export function ChatProvider({ children }: { children: React.ReactNode }) {
  return (
    <ChatContext.Provider value={{ chatService: defaultChatService }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatService() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChatService must be used within a ChatProvider');
  }
  return context;
}