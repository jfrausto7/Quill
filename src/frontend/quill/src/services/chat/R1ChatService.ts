import { ChatService } from './ChatService';

export class R1ChatService implements ChatService {
  async generateResponse(message: string, context: any): Promise<string> {
    console.log('R1ChatService: Sending message:', message);
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, context })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to get response');
      }

      const data = await response.json();
      console.log('R1ChatService: Received response:', data);
      return data.content;
    } catch (error) {
      console.error('R1ChatService: Error:', error);
      throw error; // Let the component handle the error
    }
  }
}