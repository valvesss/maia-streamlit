# Built-in libraries
import os
import concurrent.futures
from uuid import uuid4
from datetime import datetime

# 3rd part libraries
from langchain.embeddings import OpenAIEmbeddings
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Local libraries
from maia.src.message import Message
from maia.engines.query import query
from maia.src.utils import Utils
from maia.src.custom_logging import log_function_execution, logger
from maia.database.supabase import SupabaseClient
from maia.database.pinecone import PineconeClient
from maia.database.s3 import S3Client

supabase_client = SupabaseClient.get_instance()
pinecone_client = PineconeClient.get_instance()
s3_client = S3Client.get_instance()
openai_embeddings = OpenAIEmbeddings()

CHUNK_SIZE = 500
CHUNK_OVERLAP = 0
AWS_S3_RAW_FILES_BUCKET = os.getenv("AWS_S3_RAW_FILE_BUCKET")

@log_function_execution
def embedd_docs_from_raw_file(file_name: str) -> list[dict]:
    # Load PDF Data
    loader = PyPDFLoader(file_name, extract_images=True)
    
    # Create Documents
    documents = loader.load_and_split()
    
    # Split Documents
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    splitted_documents = text_splitter.split_documents(documents)
    
    # Create embedded vectors
    embedded_docs = []
    ids = [str(uuid4()) for _ in splitted_documents]

    def process_document(document, document_id):
        embedding = openai_embeddings.embed_query(document.page_content)
        metadata = {}
        metadata['source'] = document.metadata['source']
        metadata['text'] = document.page_content
        metadata['page_number'] = document.metadata['page']
        vector = {
            "id": document_id,
            "values": embedding,
            "metadata": metadata
        }
        return vector

    with concurrent.futures.ThreadPoolExecutor(max_workers=35) as executor:
        futures = [executor.submit(process_document, document, ids[i]) for i, document in enumerate(documents)]

        for future in concurrent.futures.as_completed(futures):
            try:
                vector = future.result()
                embedded_docs.append(vector)
            except Exception as e:
                logger.error(f"embedd_docs_from_raw_file: process_document: Error processing document: {e}")
        
    return embedded_docs

@log_function_execution
def load_embeddings_to_vetorial_db(user_id: str, file_id: str, embedded_docs: list) -> None:
    # Set namespace as user_id + chat
    namespace = f"{user_id}.{file_id}"
    
    # Upload vectors to Pinecone
    pinecone_client.upsert(vectors=embedded_docs, namespace=namespace, batch_size=32)

@log_function_execution
def update_file_status_to(file_id: str, status: str, extra: dict = None) -> None:
    
    # Regular Schema
    to_update = {
        'status': status,
        'updated_at': datetime.now().isoformat()
    }
    
    # In case of kargs
    if extra:
        for key, value in extra.items():
            to_update[key] = value

    supabase_client.table('files').update(to_update).eq('id', file_id).execute()

@log_function_execution
def embed(user_id: str, file: dict, tmp_raw_file_path: str = None) -> None:
    """
    1. Download source file or get from local file path
    2. Create embeddings from file
    3. Upload embeddings to vetorial DB
    4. Move raw embeddings/source file to AWS S3
    5. Delete local raw embeddings/source file
    """
    logger.info(f"EmbeddingMotor instanciated for user {user_id} on file {file['id']}")
    
    try:
        if not tmp_raw_file_path:
            # Download file from Wix
            downloaded_file_bytes = Utils().download_raw_file(file['wix_download_url'])
            
            # Write Raw file to filesystem
            tmp_raw_file_path = Utils().write_raw_file_bytes_to_fs(file['name'], downloaded_file_bytes)
        
        # Update file status
        update_file_status_to(file['id'], 'Processando')
        
        # Create embedded docs
        embedded_docs = embedd_docs_from_raw_file(tmp_raw_file_path)
        
        # Load embedded docs to vetorial db
        load_embeddings_to_vetorial_db(user_id, file['chat_id'], embedded_docs)
        
        # Update file status
        extra_data_to_update = {
            'chunk_size': CHUNK_SIZE,
            'chunk_overlap': CHUNK_OVERLAP
        }
        
        # Write startup message
        namespace = f"{user_id}.{file['chat_id']}"
        startup_question = "Resuma o documento e sugira de em formato de lista 3 perguntas que poderiam ser feitas a esse documento."
        llm_response = query(namespace, startup_question)
        if llm_response['error']:
            Message().save_message_metadata(user_id, file['chat_id'], startup_question, llm_response, "system", "error")
            logger.error("Failed to write startup message, error: ")
        else:
            Message().write_to_chat(llm_response['output_message'], "assistant", file['chat_id'])
            Message().save_message_metadata(user_id, file['chat_id'], startup_question, llm_response)


        update_file_status_to(file['id'], 'Pronto', extra_data_to_update)
        
        # Compress raw file
        # compressed_file_path = file['name'] + ".gz"
        # Utils().compress_file(tmp_raw_file_path, compressed_file_path)
        
        # Moves file to S3
        Utils().move_file_to_s3(tmp_raw_file_path, file['s3_raw_file_key'])
        
        # Deletes raw file
        Utils().delete_local_file(tmp_raw_file_path)
        
        # Deletes temp file
        # Utils().delete_local_file(compressed_file_path)
        
        # Compress embedded_docs
        bytes_compressed_embedded_docs = Utils().compress_dict(embedded_docs)
        
        # Moves compressed embedded docs to s3
        Utils().move_bytes_to_s3(bytes_compressed_embedded_docs, file['s3_vectors_key'])
        
        logger.info(f"EmbeddingMotor finished for user {user_id} on file {file['id']}")
    except Exception as e:
        logger.error(f"engine.embed: Error trying to embed for user {user_id} on file {file['id']}: {e}")
        update_file_status_to(file['id'], 'Erro')
        