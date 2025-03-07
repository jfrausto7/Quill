import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

export async function GET(request: NextRequest) {
  try {
    // Extract file path from URL
    const url = new URL(request.url);
    const filePath = url.searchParams.get('path');

    if (!filePath) {
      return NextResponse.json({ error: 'No file path provided' }, { status: 400 });
    }

    // Remove any relative path navigation that might be in the filename
    const fileName = path.basename(filePath);
    
    // Try multiple possible upload directory locations
    const projectRoot = process.cwd();
    const possibleUploadDirs = [
      path.join(projectRoot, 'uploads'),
      path.join(projectRoot, 'src', 'uploads'),
      path.join(projectRoot, '../uploads'),
      path.join(projectRoot, '../../uploads')
    ];

    console.log('Looking for file:', fileName);
    console.log('Project root:', projectRoot);
    console.log('Possible upload directories:', possibleUploadDirs);
    
    // Try to find the file in any of the possible upload directories
    let fileFound = false;
    let fullPath = '';
    let attempts = [];

    for (const uploadsDir of possibleUploadDirs) {
      const testPath = path.join(uploadsDir, fileName);
      attempts.push(testPath);
      try {
        await fs.access(testPath);
        fullPath = testPath;
        fileFound = true;
        console.log('File found at:', fullPath);
        break;
      } catch (error) {
        // File not found in this directory, try next
        console.log(`File not found in ${testPath}`);
      }
    }

    if (!fileFound) {
      console.error('File not found in any of the possible locations');
      return NextResponse.json({ 
        error: 'File not found',
        fileName: fileName,
        searchedLocations: attempts
      }, { status: 404 });
    }

    // Read file
    const file = await fs.readFile(fullPath);
    
    // Determine content type based on file extension
    const ext = path.extname(fullPath).toLowerCase();
    let contentType = 'application/octet-stream';
    
    if (ext === '.pdf') {
      contentType = 'application/pdf';
    } else if (['.jpg', '.jpeg'].includes(ext)) {
      contentType = 'image/jpeg';
    } else if (ext === '.png') {
      contentType = 'image/png';
    }

    // Return file as response for inline display
    return new NextResponse(file, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': 'inline',
      },
    });
  } catch (error) {
    console.error('Preview error:', error);
    return NextResponse.json({ 
      error: 'Failed to preview file',
      details: error.message
    }, { status: 500 });
  }
}