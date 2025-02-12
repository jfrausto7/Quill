export class ChatService {
  async generateResponse(
    message: string, 
    context: { 
      documents: Array<{ name: string; type: string }>;
      chatHistory: Array<{ type: string; content: string }>;
    }
  ): Promise<string> {
    try {
      // Get the most recently uploaded document
      const latestDocument = context.documents[context.documents.length - 1];
      if (!latestDocument) {
        return "Please upload a document first before asking questions.";
      }

      const formData = new FormData();
      formData.append('mode', 'query');
      formData.append('message', message);
      formData.append('documentName', latestDocument.name);
      
      // Add chat history for context
      formData.append('chatHistory', JSON.stringify(context.chatHistory));

      const response = await fetch('/api/rag', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to get response from RAG system');
      }

      const data = await response.json();
      return data.content;
    } catch (error) {
      console.error('ChatService error:', error);
      throw error;
    }
  }
}