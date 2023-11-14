# Built-in libraries
import os
from threading import Thread
from typing import Optional
from datetime import datetime

# Local libraries
from maia.engines.query import query
from maia.src.user import User
from maia.src.message import Message
from maia.src.custom_logging import log_function_execution, logger
from maia.database.supabase import SupabaseClient

supabase_client = SupabaseClient.get_instance()

SUB_PLAN_1_MAX_AI_INTERACTIONS = os.getenv("SUB_PLAN_1_MAX_AI_INTERACTIONS")

class Chat(object):
    def __init__(self, user_id: str, chat_id: str = None) -> None:
        self.supabase_client = supabase_client
        self.user_id = user_id
        self.chat_id = chat_id
    
    @log_function_execution
    def get_all(self, is_archived: bool = False) -> list[dict[str, any]]:
        
        """
        Gets all supabase chats.

        Returns:
            list[dict]: A list of chat dictionaries.
        """
        chats, _ = self.supabase_client.table('chats') \
                                       .select('*') \
                                       .eq('user_id', self.user_id) \
                                       .eq('is_archived', is_archived) \
                                       .execute()
        return chats[1]
    
    @log_function_execution
    def get_one(self, is_archived: bool = False) -> Optional[dict | None]:
        """
        Fetches a chat by its ID and returns it as a Chat object.
        
        Args:
            is_archived bool: If Chat is Archived ot not
            
        Returns
            [{}]: List with dict chat content
            None: For no Chat ID found
        
        """
        chat, _ = self.supabase_client.table('chats') \
                                      .select('*') \
                                      .eq('id', self.chat_id) \
                                      .eq('user_id', self.user_id) \
                                      .eq('is_archived', is_archived) \
                                      .execute()

        if chat[1]:
            return chat[1][0]
        return None
    
    @log_function_execution
    def create(self, file_id: str) -> dict:
        """
        Creates a new chat.

        Args:
            file_id (str): The file ID ref for the chat.
            chat_id (str): ID created at Files.

        Returns:
            dict: The created chat.
        """
        # Define default chat body
        chat = {}
        chat['id'] = self.chat_id
        chat['name'] = "Random"
        chat['file_id'] = file_id
        chat['user_id'] = self.user_id
        chat['namespace'] = f"{self.user_id}.{self.chat_id}"
        chat['status'] = "activating"
        chat['archived_at'] = None
        chat['is_archived'] = False
        chat['created_at'] = datetime.now().isoformat()
        
        return chat
  
    @log_function_execution
    def archive(self) -> bool:
        """
        Flags a Chat as archived.

        Args:
            chat_id (Union[str, int]): The ID of the chat to archive.

        Returns:
            bool: True if successful, False otherwise.
        """
        data, _ = self.supabase_client.table('chats') \
                                      .update({'is_archived': True, 
                                               'archived_at': datetime.now().isoformat()}) \
                                      .eq('user_id', self.user_id) \
                                      .eq('id', self.chat_id) \
                                      .eq('is_archived', False) \
                                      .execute()
                   
        if data[1]:
            return data[1][0]
        return None
    
    @log_function_execution
    def has_user_reached_max_interactions(self, user: dict) -> bool:
        user_service = User()
        max_ai_interactions = user_service.get_user_max_ai_interactions(
            user['subscription_plan_id'], user['custom_max_interactions'])
        user_current_ai_interactions = user_service.get_user_current_monthly_ai_interactions(user['id'])
        if user_current_ai_interactions == None:
            user_current_ai_interactions = 0

        if user_current_ai_interactions >= max_ai_interactions:
            return True
        else:
            return False
        
    @log_function_execution
    def send_message(self, user: dict, content: str, role: str) -> None:
        
        # Write incoming message
        Thread(target=Message().write_to_chat, args=(content, role, self.chat_id)).start()
        
        # Validate user limits
        is_limit_reached = self.has_user_reached_max_interactions(user)
        if is_limit_reached:
            self._handle_max_interactions()
        else:
            self.process_incoming_message(content)

    @log_function_execution
    def _handle_max_interactions(self):
        # Write the system message for max interactions
        max_message_warn = "Limite máximo de mensagens atingido! Por favor, faça um upgrade de plano ou mande um email para suporte@ninev.co."
        Message().write_to_chat(max_message_warn, "system", self.chat_id)

    @log_function_execution
    def process_incoming_message(self, input_message: str) -> None:
        
        # Set default error message
        error_chat_message = "Ocorreu um erro durante sua requisição, por favor contate o suporte através de: suporte@ninev.co!"
        
        # Set handlers
        message_writer = Message()
        user_handler = User()
        namespace = f"{self.user_id}.{self.chat_id}"
        
        # Start the AI query in a separate thread
        try:
            llm_response = query(namespace, input_message)
        except Exception as e:
            logger.error(f"query: Unexpected error: {e}")
            message_writer.write_to_chat(error_chat_message, "system", self.chat_id)
        
        # In case any error is escaped from OpenAI LLM
        if llm_response['error']:
            message_writer.write_to_chat(error_chat_message, "system", self.chat_id)
            message_writer.save_message_metadata(self.user_id, self.chat_id, input_message, llm_response, "system", "error")
        else:    
            message_writer.write_to_chat(llm_response['output_message'], "assistant", self.chat_id)
            message_writer.save_message_metadata(self.user_id, self.chat_id, input_message, llm_response)
        
            user_handler.increment_user_current_ai_interactions(self.user_id)
            user_handler.increment_user_monthly_ai_interactions(self.user_id)
            
