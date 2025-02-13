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
  const quotedArgs = args.map(arg => {
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

        const llamaScriptPath = path.join('..', '..', 'llama3.2-vision', 'llama-interface.py');
        try {
          await fs.access(llamaScriptPath);
          console.log('Llama script found at:', llamaScriptPath);
        } catch (error) {
          console.error('Llama script not found:', error);
          return NextResponse.json({ error: 'Llama script not found' }, { status: 500 });
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
            llamaScriptPath, 
            ['--mode', 'ingest', '--file', filePath]
        );

        try {
          const result = JSON.parse(stdout);
          return NextResponse.json(result);
        } catch {
            return NextResponse.json({
                message: 'Document uploaded successfully',
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
              error: 'Missing required fields' 
            }, { status: 400 });
        }

        const documentPath = path.join('..', '..', 'uploads', documentName as string);
        const args = ['--mode', 'query', '--document', documentPath, '--question', message as string];
        if (chatHistory) {
            const tempChatHistoryPath = path.join('..', '..', 'uploads', 'temp_chat_history.json');
            await writeFile(tempChatHistoryPath, chatHistory as string);
            args.push('--chat-history', tempChatHistoryPath);
        }

        const { stdout } = await runPythonScript(llamaScriptPath, args);

        try {
          const result = JSON.parse(stdout);
          return NextResponse.json({ content: result.response });
        } catch {
          return NextResponse.json({ content: stdout.trim});
        }
    }

    return NextResponse.json({ error: 'Invalid mode' }, { status: 400 });
    } catch (error) {
        console.error('Error processing request:', error);
        return NextResponse.json({
            error: 'Failed to process request',
            details: error.message
        },
        { status: 500 }
        );
    }
}