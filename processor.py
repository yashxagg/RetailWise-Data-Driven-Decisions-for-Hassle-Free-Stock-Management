import os
from groq import Groq
from PyPDF2 import PdfReader
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq client
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

def extract_text_from_pdf(pdf_file_path):
    """
    Extracts text from a PDF file path or file-like object.
    Args:
        pdf_file_path: Path to the PDF file or file-like object
    Returns:
        str: Extracted text
    """
    try:
        reader = PdfReader(pdf_file_path)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_keywords_ai(text, top_n=15):
    """
    Extracts keywords using Groq API (Llama 3).
    Args:
        text (str): The text content
        top_n (int): Number of keywords to extract
    Returns:
        list: List of extracted keywords
    """
    if not text or len(text.strip()) < 10:
        return []

    # Truncate text if it's too long for the context window (roughly)
    # 1 token ~= 4 chars, safe limit for now
    truncated_text = text[:15000] 

    system_prompt = "You are a specialized financial analyst AI. Your task is to extract relevant financial and retail stock analysis keywords from the provided text."
    
    user_prompt = f"""
    Extract the top {top_n} most important keywords, stock tickers, or financial terms from the text below. 
    Return ONLY a comma-separated list of keywords. Do not include numbering, bullet points, or any introductory text.
    
    Text:
    {truncated_text}
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        
        # Parse response
        response_content = chat_completion.choices[0].message.content
        
        # Clean up the response to get a list
        keywords = [k.strip() for k in response_content.split(',') if k.strip()]
        return keywords

    except Exception as e:
        print(f"Groq API Error: {e}")
        return []
