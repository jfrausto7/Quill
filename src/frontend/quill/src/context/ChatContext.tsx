'use client';

import React, { createContext, useContext } from 'react';
import { ChatService } from '@/services/chat/ChatService';
import { R1ChatService } from '@/services/chat/R1ChatService';
import { RAGChatService } from '@/services/chat/RAGChatService';

interface ChatContextType {
  chatService: ChatService;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

// You can switch between services based on your needs
const defaultChatService = new RAGChatService(); // or R1ChatService() if you want that as default

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