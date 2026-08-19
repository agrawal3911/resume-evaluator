import pymupdf as fitz
from app.parsers.document_parser import parse_document


# 1. Create a sample PDF file programmatically for this demonstration
pdf_path = "sample_resume.pdf"
doc = fitz.open()
page = doc.new_page()
sample_text = """JOHN DOE
Software Engineer

Experience
Senior Developer at Tech Corp
2020 - Present
- Led the migration of legacy monolith to microservices.
- Improved database query performance by 40%.

Education
B.S. in Computer Science
University of Technology, 2019"""
page.insert_text((50, 50), sample_text)
doc.save(pdf_path)
doc.close()

print(f"--- Successfully created {pdf_path} ---")

# 2. Test the PDF parser
print("\n--- Starting PDF Parsing ---")
try:
    # Read the file as raw bytes
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    # Pass the bytes and filename to our router
    extracted_text = parse_document(file_bytes, pdf_path)
    
    print("\n--- Extracted and Cleaned Text ---")
    print(extracted_text)
    print("\n--- Parsing Successful! ---")
    
except Exception as e:
    print(f"Error parsing document: {e}")
