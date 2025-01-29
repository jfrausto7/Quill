export interface ChatService {
    generateResponse(
      message: string,
      context: {
        documents: Array<{
          id: number;
          name: string;
          type: string;
        }>;
        chatHistory: Array<{
          type: 'user' | 'bot';
          content: string;
        }>;
      }
    ): Promise<string>;
  }