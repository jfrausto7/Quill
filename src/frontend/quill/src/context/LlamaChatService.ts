import { ChatService } from './ChatService';

export class LlamaChatService implements ChatService {
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
            const response = await fetch('/api/documents');
            if (!response.ok) {
                throw new Error('Failed to fetch document list');
        }
        const actualFiles = await response.json();
        if (!actualFiles.length) {
            return "Please upload a document first before asking questions.";
        }
        const latestFile = actualFiles[actualFiles.length - 1];
        const formData = new FormData();
        formData.append('mode', 'query');
        formData.append('message', message);
        formData.append('documentName', latestFile.name);
        formData.append('chatHistory', JSON.stringify(context.chatHistory));
        const llamaResponse = await fetch('/api/llama', {
            method: 'POST',
            body: formData,
        });
        if (!llamaResponse.ok) {
            throw new Error('Failed to get response from Llama system');
        }
        const responseData = await llamaResponse.json();
        return responseData;
        } catch (error) {
            console.error('Error generating response:', error);
            throw error;
        }
    }
}