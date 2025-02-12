import { exec } from 'child_process';
import { promisify } from 'util';
import { NextResponse } from 'next/server';
import os from 'os';
import { writeFile } from 'fs/promises';
import path from 'path';
import fs from 'fs/promises';

const execPromise = promisify(exec);

async function saveUploadedFile(file: Buffer, fileName: string): Promise<string> {
  try {
    const uploadsDir = path.join('..', '..', 'uploads');
    try {
      await fs.access(uploadsDir);
    } catch {
      await fs.mkdir(uploadsDir, { recursive: true });
    }

    const filePath = path.join(uploadsDir, fileName);
    await writeFile(filePath, file);
    console.log('File saved successfully at:', filePath);
    return filePath;
  } catch (error) {
    console.error('Error saving file:', error);
    throw error;
  }
}

async function runPythonScript(scriptPath: string, args: string[]) {
  const isWindows = os.platform() === 'win32';
  const condaEnv = 'quill';

  // Properly escape and quote arguments, especially JSON strings
  const quotedArgs = args.map(arg => {
    // If the argument contains spaces or special characters, wrap it in quotes
    // and escape any existing quotes
    if (arg.includes(' ') || arg.includes('"') || arg.includes("'") || arg.includes('{')) {
      const escapedArg = arg.replace(/"/g, '\\"');
      return `"${escapedArg}"`;
    }
    return arg;
  }).join(' ');

  let command;
  if (isWindows) {
    command = `conda run -n ${condaEnv} python "${scriptPath}" ${quotedArgs}`;
  } else {
    command = `python3 "${scriptPath}" ${quotedArgs}`;
  }
  
  console.log('Executing command:', command);
  
  try {
    const result = await execPromise(command);
    console.log('Python script stdout:', result.stdout);
    if (result.stderr) {
      console.log('Python script stderr:', result.stderr);
    }
    return result;
  } catch (error) {
    console.error('Error running Python script:', error);
    throw error;
  }
}

export async function POST(request: Request) {
  try {
    console.log('Starting POST request processing');
    const formData = await request.formData();
    const mode = formData.get('mode');
    console.log('Request mode:', mode);

    const ragScriptPath = path.join('..', '..', 'rag', 'quill_rag.py');
    try {
      await fs.access(ragScriptPath);
      console.log('RAG script found at:', ragScriptPath);
    } catch (error) {
      console.error('RAG script not found:', error);
      return NextResponse.json(
        { error: 'RAG script not found', details: error.message },
        { status: 500 }
      );
    }

    if (mode === 'ingest') {
      const file = formData.get('file') as File;
      if (!file) {
        return NextResponse.json({ error: 'No file provided' }, { status: 400 });
      }

      console.log('Processing file:', file.name);
      const buffer = Buffer.from(await file.arrayBuffer());
      const filePath = await saveUploadedFile(buffer, file.name);

      const { stdout } = await runPythonScript(
        ragScriptPath,
        ['--mode', 'ingest', '--document', filePath]
      );

      try {
        const result = JSON.parse(stdout);
        return NextResponse.json(result);
      } catch {
        return NextResponse.json({ 
          message: 'Document processed successfully',
          details: stdout 
        });
      }
    } 
    else if (mode === 'query') {
      const message = formData.get('message');
      const documentName = formData.get('documentName');
      const chatHistory = formData.get('chatHistory');

      if (!message || !documentName) {
        return NextResponse.json({ 
          error: 'Message and document name are required' 
        }, { status: 400 });
      }

      const documentPath = path.join('..', '..', 'uploads', documentName as string);
      
      // Build args array without the chat history first
      const args = ['--mode', 'query', '--document', documentPath, '--question', message as string];
      
      // Add chat history separately if it exists
      // Write chat history to a temporary file instead of passing it directly
      if (chatHistory) {
        const tempChatHistoryPath = path.join('..', '..', 'uploads', 'temp_chat_history.json');
        await writeFile(tempChatHistoryPath, chatHistory as string);
        args.push('--chat-history', tempChatHistoryPath);
      }

      const { stdout } = await runPythonScript(ragScriptPath, args);

      try {
        const result = JSON.parse(stdout);
        return NextResponse.json({ content: result.response });
      } catch {
        return NextResponse.json({ content: stdout.trim() });
      }
    }

    return NextResponse.json({ error: 'Invalid mode' }, { status: 400 });
  } catch (error) {
    console.error('Route error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to process request',
        details: error.message,
      },
      { status: 500 }
    );
  }
}