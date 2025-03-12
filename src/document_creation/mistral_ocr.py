from mistralai import Mistral
import os

def main():
    api_key = os.getenv("MISTRAL_API_KEY")

    client = Mistral(api_key=api_key)

    uploaded_pdf = client.files.upload(
        file={
            "file_name": "uploaded_file.pdf",
            "content": open("images/W-2.pdf", "rb"),
        },
        purpose="ocr"
    )  

    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url,
        }
    )
    
    print(ocr_response)

if __name__ == "__main__":
    main()