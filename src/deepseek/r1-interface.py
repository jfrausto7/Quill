import sys
import ollama
import json
import base64
import PyPDF2
from io import BytesIO
import mammoth

def extract_text_from_pdf(pdf_content):
    try:
        # Debug logging
        print("\n=== DEBUG: PDF PROCESSING START ===", file=sys.stderr)
        print(f"1. Content Type: {type(pdf_content)}", file=sys.stderr)
        print(f"2. Content Length: {len(pdf_content) if isinstance(pdf_content, (str, bytes)) else 'N/A'}", file=sys.stderr)
        
        # If it's a string, print the first and last 100 characters
        if isinstance(pdf_content, str):
            print("\n3. Content Preview (first 100 chars):", file=sys.stderr)
            print(pdf_content[:100], file=sys.stderr)
            print("\n4. Content Preview (last 100 chars):", file=sys.stderr)
            print(pdf_content[-100:], file=sys.stderr)

        # Handle base64 PDF data
        if isinstance(pdf_content, str):
            if pdf_content.startswith('data:application/pdf;base64,'):
                print("\n5. Detected base64 PDF with data URL prefix", file=sys.stderr)
                pdf_content = pdf_content.split('base64,')[1]
            pdf_content = pdf_content.strip()
            try:
                pdf_bytes = base64.b64decode(pdf_content, validate=True)
                print(f"\n6. Successfully decoded base64. Decoded length: {len(pdf_bytes)} bytes", file=sys.stderr)
                # Print first few bytes to verify PDF header
                print(f"7. First 20 bytes: {pdf_bytes[:20]}", file=sys.stderr)
            except Exception as e:
                print(f"\n6. Base64 decode error: {e}", file=sys.stderr)
                return f"Error: Invalid PDF data - {str(e)}"
        else:
            return "Error: Expected base64 encoded PDF data"

        # Validate PDF header
        if not pdf_bytes.startswith(b'%PDF'):
            print("\n8. ERROR: Invalid PDF header!", file=sys.stderr)
            return "Error: Invalid PDF format - Missing PDF header"
        else:
            print("\n8. Valid PDF header detected", file=sys.stderr)

        # Create BytesIO object
        pdf_file = BytesIO(pdf_bytes)
        
        try:
            # Create PDF reader
            pdf_reader = PyPDF2.PdfReader(pdf_file, strict=False)
            print(f"\n9. Successfully created PDF reader. Pages: {len(pdf_reader.pages)}", file=sys.stderr)
            
            # Extract text with error handling for each page
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(text.strip())
                        print(f"\n10. Successfully extracted text from page {page_num + 1}. Length: {len(text)}", file=sys.stderr)
                    else:
                        print(f"\n10. No text found on page {page_num + 1}", file=sys.stderr)
                except Exception as page_error:
                    print(f"\n10. Error on page {page_num + 1}: {page_error}", file=sys.stderr)
                    continue
            
            if not text_parts:
                print("\n11. WARNING: No text extracted from any pages!", file=sys.stderr)
                return "Error: No text could be extracted from PDF"
            
            final_text = "\n\n".join(text_parts)
            print(f"\n11. Total extracted text length: {len(final_text)}", file=sys.stderr)
            print("\n12. First 500 chars of extracted text:", file=sys.stderr)
            print(final_text[:500], file=sys.stderr)
            print("\n=== DEBUG: PDF PROCESSING END ===\n", file=sys.stderr)
                
            return final_text
            
        except PyPDF2.errors.PdfReadError as e:
            print(f"\nPyPDF2 error: {e}", file=sys.stderr)
            return f"Error: PDF reading error - {str(e)}"
            
    except Exception as e:
        print(f"\nError extracting text from PDF: {e}", file=sys.stderr)
        return f"Error: Could not process PDF - {str(e)}"

def extract_text_from_docx(docx_content):
    try:
        print("\n=== DEBUG: DOCX PROCESSING START ===", file=sys.stderr)
        
        # Convert base64 to bytes if needed
        if isinstance(docx_content, str):
            if docx_content.startswith('data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,'):
                docx_content = docx_content.split('base64,')[1]
            docx_content = docx_content.strip()
            docx_bytes = base64.b64decode(docx_content, validate=True)
        else:
            return "Error: Expected base64 encoded DOCX data"

        # Create BytesIO object
        docx_file = BytesIO(docx_bytes)
        
        # Extract text using mammoth
        result = mammoth.extract_raw_text(docx_file)
        text = result.value
        
        if not text.strip():
            print("\nWARNING: No text extracted from DOCX!", file=sys.stderr)
            return "Error: No text could be extracted from DOCX"
            
        print(f"\nTotal extracted text length: {len(text)}", file=sys.stderr)
        print("\n=== DEBUG: DOCX PROCESSING END ===\n", file=sys.stderr)
        
        return text.strip()
        
    except Exception as e:
        print(f"\nError extracting text from DOCX: {e}", file=sys.stderr)
        return f"Error: Could not process DOCX - {str(e)}"

def format_document_context(documents):
    if not documents:
        return ""
        
    context = "Available documents:\n\n"
    for doc in documents:
        try:
            context += f"Document: {doc['name']}\n"
            
            # Print debug info
            print(f"Processing document: {doc['name']}", file=sys.stderr)
            print(f"Content type: {type(doc['content'])}", file=sys.stderr)
            
            # Get the content based on file type
            file_name = doc['name'].lower()
            if file_name.endswith('.pdf'):
                content = extract_text_from_pdf(doc['content'])
            elif file_name.endswith('.docx'):
                content = extract_text_from_docx(doc['content'])
            elif file_name.endswith('.doc'):
                # For old .doc files, inform user to convert to .docx
                content = "Error: Legacy .doc files are not supported. Please convert to .docx format."
            else:
                try:
                    if isinstance(doc['content'], str):
                        try:
                            content = base64.b64decode(doc['content'].encode('utf-8')).decode('utf-8')
                        except:
                            content = doc['content']
                    else:
                        content = doc['content']
                except:
                    content = str(doc['content'])
                
            # Check for extraction errors
            if content.startswith('Error:'):
                print(f"Warning: {content}", file=sys.stderr)
                context += f"Content: {content}\n"
            else:
                # Truncate very long content
                if len(content) > 2000:
                    content = content[:2000] + "... (truncated)"
                context += f"Content: {content}\n"
                
            context += "-" * 50 + "\n"
            
        except Exception as e:
            print(f"Error processing document {doc.get('name', 'unknown')}: {e}", file=sys.stderr)
            context += f"Error processing document: {str(e)}\n"
            context += "-" * 50 + "\n"
            
    return context

def clean_response(text):
    # Remove any XML-style tags
    text = text.replace('<userStyle>Normal</userStyle>', '')
    
    # Get content after </think> tag if present
    think_splits = text.split('</think>')
    if len(think_splits) > 1:
        text = think_splits[-1]
    
    return text.strip()

def send_query(message, documents_b64=None):
    try:
        # Handle document decoding
        documents = None
        if documents_b64:
            try:
                # First decode the base64-encoded JSON string
                documents_json = base64.b64decode(documents_b64).decode('utf-8')
                documents = json.loads(documents_json)
                
                # Additional validation
                if not isinstance(documents, list):
                    raise ValueError("Documents must be a list")
                    
                print(f"Successfully decoded {len(documents)} documents", file=sys.stderr)
                print(f"Document types: {[type(doc['content']).__name__ for doc in documents]}", file=sys.stderr)
                
            except Exception as e:
                print(f"Error decoding documents: {e}", file=sys.stderr)
                return "Error: Could not decode document data"

        # Format context with documents if available
        context = format_document_context(documents) if documents else ""
        
        # Create system prompt
        system_prompt = f"""You are Quill, an AI assistant helping with documents and forms.
        
Current document context:
{context}

When answering:
1. Reference specific documents by name when using their information
2. If information isn't in the documents, say so
3. Keep responses clear and concise
4. Don't include any XML tags in your response"""

        # Get response from model
        response = ollama.chat(
            'deepseek-r1:1.5b',
            messages=[
                {
                    'role': 'system',
                    'content': system_prompt
                },
                {
                    'role': 'user',
                    'content': message,
                },
            ]
        )

        # Clean and return the response
        cleaned_response = clean_response(response['message']['content'])
        return cleaned_response or "I apologize, but I couldn't generate a proper response."

    except Exception as e:
        print(f"Error in send_query: {str(e)}", file=sys.stderr)
        return f"I encountered an error: {str(e)}"

if __name__ == "__main__":
    try:
        message = sys.argv[1]
        documents_b64 = sys.argv[2] if len(sys.argv) > 2 else None
        result = send_query(message, documents_b64)
        print(result)
    except Exception as e:
        print(f"Error in main: {str(e)}", file=sys.stderr)
        sys.exit(1)