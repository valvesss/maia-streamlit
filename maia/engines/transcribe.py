from datetime import datetime

# 3rd part modules
import openai
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# Local libraries
from maia.engines.embed import embed
from maia.src.utils import Utils
from maia.src.user import User
from maia.src.custom_logging import log_function_execution, logger
from maia.database.supabase import SupabaseClient

supabase_client = SupabaseClient()

@log_function_execution
def transcribe_audio_bytes_like(audio_file_bytes: bytes) -> str:
    
    # Get file-like opened as binary
    response = openai.Audio.transcribe("whisper-1", audio_file_bytes)
    
    # Append UTF-8 transcript to the list
    return response.text.encode('utf-8').decode('utf-8')

@log_function_execution
def create_pdf(text: str) -> str:
    # Tmp pdf file
    tmp_pdf_file = "output.pdf"
    
    # Create a new PDF document
    doc = SimpleDocTemplate(tmp_pdf_file, pagesize=letter)

    # Define the styles for paragraphs
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    
    text = text.replace('\n', '<br/>')
    
    # Create a paragraph with the text and add it to the elements list
    paragraph = Paragraph(text, normal_style)

    # Build the PDF document with the elements list
    doc.build([paragraph])
    
    return tmp_pdf_file

@log_function_execution
def transcribe(user_id: str, file: dict) -> None:
    
    # Download raw temp file
    downloaded_file_bytes = Utils().download_raw_file(file["wix_download_url"])
    
    # Write Raw file to filesystem
    tmp_raw_file_path = Utils().write_raw_file_bytes_to_fs(file['original_name'], downloaded_file_bytes)
    supabase_client.update('files',  file['id'], {'status': 'Transcrevendo', 'updated_at': datetime.now().isoformat()})
    
    # Load file in binary format to memory
    loaded_file = open(tmp_raw_file_path, "rb")
    
    # Get transcript from OpenAI
    transcription = transcribe_audio_bytes_like(loaded_file)
    
    # Remove the temporary file after use
    Utils().delete_local_file(tmp_raw_file_path)
    User().increment_user_monthly_audio_seconds(user_id, file['audio_seconds'])
    
    # Create PDF
    temp_pdf_file_path = create_pdf(transcription)

    embed(user_id, file, temp_pdf_file_path)
    
        