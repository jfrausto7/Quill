import { exec } from 'child_process';
import { promisify } from 'util';
import { NextResponse } from 'next/server';
import os from 'os';

const execPromise = promisify(exec);

async function runPythonScript(scriptPath: string, message: string) {
  const isWindows = os.platform() === 'win32';
  const condaEnv = 'base'; // Change this to your conda environment name

  let command;
  if (isWindows) {
    command = `conda run -n ${condaEnv} python "${scriptPath}" "${message}"`;
  } else {
    // On Mac/Linux, try python3 first, fall back to conda if needed
    command = `python3 "${scriptPath}" "${message}"`;
  }
  
  console.log('Executing command:', command);
  return execPromise(command).catch(async (error) => {
    if (!isWindows) {
      // If python3 fails on Mac/Linux, try conda
      command = `conda run -n ${condaEnv} python "${scriptPath}" "${message}"`;
      return execPromise(command);
    }
    throw error;
  });
}

export async function POST(request: Request) {
  try {
    const { message } = await request.json();
    console.log('API Route: Received message:', message);

    const { stdout, stderr } = await runPythonScript(
      '../../llama3.2-vision/llama-interface.py',
      message
    );

    if (stderr) {
      console.error('API Route: Python script error:', stderr);
      return NextResponse.json({ error: stderr }, { status: 500 });
    }

    // Only remove XML-like tags, keep emojis and other special characters
    const cleanedResponse = stdout
      .replace(/<[^>]+>/g, '') // Remove XML-like tags
      .trim();                 // Remove leading/trailing whitespace

    console.log('API Route: Cleaned response:', cleanedResponse);
    return NextResponse.json({ content: cleanedResponse });
  } catch (error) {
    console.error('API Route: Error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to process request',
        details: error.message,
        command: error.cmd
      },
      { status: 500 }
    );
  }
}