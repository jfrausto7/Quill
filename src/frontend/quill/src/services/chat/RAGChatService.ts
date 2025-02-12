import { ChatService } from './ChatService';

export class RAGChatService implements ChatService {
  async generateResponse(
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
  ): Promise<string> {
    try {
      // First, get list of actual files from uploads directory
      const response = await fetch('/api/documents');
      if (!response.ok) {
        throw new Error('Failed to fetch document list');
      }
      
      const actualFiles = await response.json();
      if (!actualFiles.length) {
        return "Please upload a document first before asking questions.";
      }

      // Use the most recently uploaded actual file
      const latestFile = actualFiles[actualFiles.length - 1];

      const formData = new FormData();
      formData.append('mode', 'query');
      formData.append('message', message);
      formData.append('documentName', latestFile.name);
      formData.append('chatHistory', JSON.stringify(context.chatHistory));

      const ragResponse = await fetch('/api/rag', {
        method: 'POST',
        body: formData,
      });

      if (!ragResponse.ok) {
        const errorData = await ragResponse.json().catch(() => ({}));
        console.error('RAG error response:', errorData);
        throw new Error(`Failed to get response from RAG system: ${errorData.error || ragResponse.statusText}`);
      }

      const data = await ragResponse.json();
      return data.content;
    } catch (error) {
      console.error('RAGChatService error:', error);
      throw error;
    }
  }
}