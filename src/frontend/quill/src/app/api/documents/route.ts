import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

export async function GET() {
  try {
    // Use the same uploads directory path as in the RAG route
    const uploadsDir = path.join('..', '..', 'uploads');
    
    try {
      await fs.access(uploadsDir);
    } catch {
      await fs.mkdir(uploadsDir, { recursive: true });
    }

    const files = await fs.readdir(uploadsDir);
    
    // Filter out temporary files and hidden files
    const documents = files
      .filter(file => 
        !file.startsWith('temp_') && 
        !file.startsWith('.') &&
        file.toLowerCase().endsWith('.pdf')
      )
      .map((name, index) => ({
        id: Date.now() + index,
        name,
        type: 'Document'
      }));

    return NextResponse.json(documents);
  } catch (error) {
    console.error('Error reading documents:', error);
    return NextResponse.json(
      { error: 'Failed to read documents' },
      { status: 500 }
    );
  }
}