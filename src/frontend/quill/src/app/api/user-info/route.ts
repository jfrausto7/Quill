import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

export async function GET() {
  try {
    // Path to the user_info.json file
    const filePath = path.join(process.cwd(), '..', '..', 'uploads', 'user_info.json');
    
    // Read the file
    const fileContent = await fs.readFile(filePath, 'utf-8');
    
    // Parse the JSON content
    const userInfo = JSON.parse(fileContent);
    
    // Return the data
    return NextResponse.json(userInfo);
  } catch (error) {
    console.error('Error reading user_info.json:', error);
    return NextResponse.json(
      { error: 'Failed to read user info' },
      { status: 500 }
    );
  }
}