import { NextRequest, NextResponse } from 'next/server';
import { MongoDocumentService } from '@/services/MongoDocumentService';

const documentService = new MongoDocumentService();

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;
    
    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      );
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    const metadata = {
      name: file.name,
      type: file.type,
      size: file.size,
      lastModified: new Date(file.lastModified),
    };

    const savedDoc = await documentService.saveDocument(
      file.name,
      buffer,
      metadata
    );

    return NextResponse.json(savedDoc);
  } catch (error) {
    console.error('Error handling file upload:', error);
    return NextResponse.json(
      { error: 'Failed to process file' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  const id = request.nextUrl.searchParams.get('id');
  
  if (!id) {
    return NextResponse.json(
      { error: 'No document ID provided' },
      { status: 400 }
    );
  }

  try {
    await documentService.deleteDocument(id);
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting document:', error);
    return NextResponse.json(
      { error: 'Failed to delete document' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  const id = request.nextUrl.searchParams.get('id');
  const isDownload = request.nextUrl.searchParams.get('download') === 'true';

  try {
    if (id && isDownload) {
      console.log('Fetching document for download:', id);
      const document = await documentService.getDocument(id);
      
      // Make sure we have the content
      if (!document.content) {
        throw new Error('Document content not found');
      }

      // Create headers for the download
      const headers = new Headers();
      headers.set('Content-Type', document.metadata?.type || 'application/octet-stream');
      headers.set('Content-Disposition', `attachment; filename="${document.name}"`);
      headers.set('Content-Length', document.content.length.toString());
      
      // Return the file as a stream
      return new NextResponse(document.content, {
        status: 200,
        headers,
      });
    }

    // List all documents
    const documents = await documentService.listDocuments();
    return NextResponse.json({ documents });
  } catch (error) {
    console.error('Error with documents:', error);
    return NextResponse.json(
      { error: 'Operation failed', details: error.message },
      { status: 500 }
    );
  }
}