export interface MessageType {
  type: 'user' | 'bot';
  content: string;
}