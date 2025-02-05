import { NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import { MongoDocumentService } from '@/services/MongoDocumentService';

const documentService = new MongoDocumentService();

export async function POST(req: Request) {
  try {
    const { message, documentIds } = await req.json();

    // If there are document IDs, fetch them
    let documentsData = [];
    if (documentIds && documentIds.length > 0) {
      for (const id of documentIds) {
        console.log(`Fetching document ${id} from MongoDB...`);
        try {
          const doc = await documentService.getDocument(id);
          
          // Determine content type based on file extension
          const getMimeType = (filename: string) => {
            const extension = filename.toLowerCase().split('.').pop();
            const mimeTypes: { [key: string]: string } = {
              'pdf': 'application/pdf',
              'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
              'doc': 'application/msword',
              'txt': 'text/plain',
              // Add more mime types as needed
            };
            return mimeTypes[extension || ''] || 'application/octet-stream';
          };

          // Convert Buffer to base64 and add data URL prefix
          const contentType = getMimeType(doc.name);
          const base64Content = doc.content.toString('base64');
          const dataUrl = `data:${contentType};base64,${base64Content}`;
          
          documentsData.push({
            name: doc.name,
            content: dataUrl,
            contentType,
            contentLength: doc.content.length,
            firstBytes: doc.content.slice(0, 15).toString('hex')
          });

          // Log document info for debugging
          console.log({
            documentName: doc.name,
            contentType: doc.content.constructor.name,
            contentLength: doc.content.length,
            firstBytes: doc.content.slice(0, 15).toString('hex')
          });

        } catch (error) {
          console.error(`Error fetching document ${id}:`, error);
          throw new Error(`Failed to fetch document ${id}`);
        }
      }
    }

    // Convert documents array to base64
    const documentsBase64 = documentsData.length > 0 
      ? Buffer.from(JSON.stringify(documentsData)).toString('base64')
      : null;

    // Create Python process
    const pythonProcess = spawn('python3', [
      path.join(process.cwd(), '../../deepseek/r1-interface.py'),
      message,
      documentsBase64 || '',
    ]);

    return new Promise((resolve, reject) => {
      let output = '';
      let stderr = '';

      pythonProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        console.error('Python stderr:', data.toString());
        stderr += data.toString();
      });

      pythonProcess.on('close', (code) => {
        if (code === 0) {
          try {
            resolve(NextResponse.json({ content: output.trim() }));
          } catch (error) {
            reject(new Error('Failed to parse Python output'));
          }
        } else {
          reject(new Error(`Process exited with code ${code}\nStderr: ${stderr}`));
        }
      });
    });
  } catch (error) {
    console.error('Error in chat:', error);
    return NextResponse.json(
      { error: 'Failed to process chat request' },
      { status: 400 }
    );
  }
}