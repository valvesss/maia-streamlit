# Built-in libraries
import os
from uuid import uuid4
from datetime import datetime

# 3rd part libraries
from rq import Queue
from postgrest.exceptions import APIError

# Local Modules
from maia.workers.files import conn
from maia.src.user import User
from maia.src.chat import Chat
from maia.engines.embed import embed
from maia.engines.transcribe import transcribe
from maia.src.custom_logging import log_function_execution, logger
from maia.src.utils import Utils
from maia.database.supabase import SupabaseClient
from maia.database.pinecone import PineconeClient

supabase_client = SupabaseClient.get_instance()
pinecone_client = PineconeClient.get_instance()

q = Queue('files_worker', connection=conn)

class File(object):
    def __init__(self, user_id: str) -> None:
        self.supabase_client = supabase_client
        self.user_id = user_id
    
    @log_function_execution
    def create_file(self, files_metadata: list[dict]) -> dict:
        """
        Creates new files and its respective chats in the database.

        Args:
            list (dict): a dict with the file name and size.
        Ex:
            [
                {
                    "name": "document1.pdf" (str)
                    "download_url": http:wix.dummy (str)
                }
            ]

        Returns:
            dict: The created file.
        """ 
        
        files = []
        chats = []
        for file_metadata in files_metadata:
            
            # Set file id
            file_id = str(uuid4())
            chat_id = str(uuid4())
            
            # Set S3 raw file paths
            if file_metadata['extension'] == 'pdf':
                file_name = file_metadata['name']
                s3_raw_file_key = f"user_id={self.user_id}/file={file_id}/{file_metadata['name']}"
            elif file_metadata['extension'] == 'mp3':
                file_name = os.path.splitext(file_metadata['name'])[0] + "_transcricao.pdf"
                s3_raw_file_key = f"user_id={self.user_id}/file={file_id}/{file_name}"
            
            # Set S3 vector paths
            s3_vectors_key = f"user_id={self.user_id}/file={file_id}/vectors.json.gz"
        
            # Get extension
            file = {}
            file['id'] = file_id
            file['_id'] = str(uuid4())
            file['name'] = file_name
            file['original_name'] = file_metadata['name']
            file['size'] = file_metadata['size']
            file['extension'] = "pdf"
            file['original_extension'] = file_metadata['extension']
            file['wix_url'] = file_metadata['wix_url']
            file['wix_download_url'] = file_metadata['wix_download_url']
            file['status'] = 'Carregando'
            file['user_id'] = self.user_id
            file['chat_id'] = chat_id
            file['audio_seconds'] = file_metadata['audio_seconds']
            file['allow_download'] = False
            file['created_at'] = datetime.now().isoformat()
            file['s3_vectors_key'] = s3_vectors_key            
            file['s3_raw_file_key'] = s3_raw_file_key
            files.append(file)
            
            chat = Chat(self.user_id, chat_id).create(file_id)
            chats.append(chat)
            
            User().increment_user_current_file_bytes_storaged(self.user_id, file_metadata['size'])
            User().increment_user_current_files_uploaded(self.user_id)
            
            self.transcribe_or_embed(file)
            
        # Store in DB
        self.supabase_client.table("files").insert(files).execute()
        self.supabase_client.table("chats").insert(chats).execute()
        
        return files
    
    @log_function_execution
    def transcribe_or_embed(self, file: dict) -> None:
        if file['original_extension'] == "pdf":
            _ = q.enqueue(embed, self.user_id, file, job_timeout=120)
        elif file['original_extension'] == "mp3":
            _ = q.enqueue(transcribe, self.user_id, file, job_timeout=120)
        else:
            logger.error("File.transcribe_or_embed ERROR: extension not known")
        
    @log_function_execution
    def get_all_files(self) -> list[dict]:
        """
        Gets all user files.

        Returns:
            list[dict]: A list of chat dictionaries.
        """
        try:
            files, _ = self.supabase_client.table('files') \
                                        .select('*') \
                                        .eq('user_id', self.user_id) \
                                        .eq('is_deleted', False) \
                                        .execute()
        except APIError:
            logger.info(f"Error trying to fetch Supabase API. Table: 'files' | Select: '*' | Filters: user_id == {self.user_id}")
            logger.info(f"APIError message: {APIError.message}")
            return []
        return files[1]
    
    @log_function_execution
    def get_one_file(self, file_id: str) -> dict:
        """
        Gets one user file.

        Returns:
            dict: the file data.
        """
        file, _ = self.supabase_client.table('files') \
                                       .select('*') \
                                       .eq('id', file_id) \
                                       .eq('user_id', self.user_id) \
                                       .eq('is_deleted', False) \
                                       .execute()
                                       
        if file[1]:
            return file[1][0]
        return None
    
    @log_function_execution
    def delete_one_file(self, file_id: str) -> dict:
        """
        Deletes one user file.
        """
        # Update is deleted Flag
        response, _ = self.supabase_client.table('files') \
                                          .update({'is_deleted': True,
                                                   'updated_at': datetime.now().isoformat()}) \
                                          .eq('id', file_id) \
                                          .eq('user_id', self.user_id) \
                                          .execute()

        # Get file data in case it exists
        if response[1]:
            file = response[1][0]
        else:
            return
        
        # Archive Chat
        response, _ = self.supabase_client.table('chats') \
                                          .update({'is_archived': True,
                                                   'updated_at': datetime.now().isoformat()}) \
                                          .eq('id', file['chat_id']) \
                                          .eq('user_id', self.user_id) \
                                          .execute()

        if response[1]:
            chat = response[1][0]

        # Delete vectors from db
        pinecone_client.delete(delete_all=True, namespace=chat['namespace'])
        
        # Delete AWS raw and vectors objects
        Utils().delete_aws_file(file['s3_raw_file_key'])
        Utils().delete_aws_file(file['s3_vectors_key'])
        
        # Decrement user bytes usage
        User().decrement_user_current_file_bytes_storaged(self.user_id, file['size'])
        User().decrement_user_current_files_uploaded(self.user_id)