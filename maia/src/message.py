from uuid import uuid4
from datetime import datetime

from maia.src.custom_logging import log_function_execution
from maia.database.supabase import SupabaseClient

supabase_client = SupabaseClient.get_instance()

class Message(object):
    @log_function_execution    
    def write_to_chat(self, content: str, role: str, chat_id: str) -> dict:
        """
        Store a receiving message inside the Chat.

        Args:
            content (str): The message content itself
            role (str): The message role sender
            chat_id (str): The Chat ID reference

        Returns:
            dict: The new created message
        """
        # Retrieve current messages
        response = supabase_client.table('chats').select('messages').eq('id', chat_id).execute()
        
        if response.data:
            current_messages = response.data[0]['messages'] or []
        else:
            # Chat ID does not exists
            return None       
        
        # Build message body
        message = {}
        message['id'] = str(uuid4())
        message['_id'] = str(len(current_messages) +1)
        message['role'] = role
        message['content'] = content
        message['created_at'] = datetime.now().isoformat()

        # Append new message to current messages
        current_messages.append(message)

        # Update messages
        supabase_client.table('chats') \
                    .update({'messages': current_messages,
                             'updated_at': datetime.now().isoformat()}) \
                    .eq('id', chat_id) \
                    .execute()    

        return message   

    @log_function_execution
    def save_message_metadata(self,
                              user_id: str, 
                              chat_id: str, 
                              input_message: str, 
                              llm_response: dict, 
                              output_role: str = "assistant",
                              status: str = "ok") -> dict:
        
        openai_callback = llm_response.get('openai_callback', {})
        total_tokens = getattr(openai_callback, 'total_tokens', 0)
        prompt_tokens = getattr(openai_callback, 'prompt_tokens', 0)
        completion_tokens = getattr(openai_callback, 'completion_tokens', 0)
        usd_cost = getattr(openai_callback, 'total_cost', 0)
        error_code = llm_response.get('error_code', None)
        error_message = llm_response.get('error_message', None)
        
        message = {
            "id": str(uuid4()),
            "user_id": user_id,
            "chat_id": chat_id,
            "created_at": datetime.now().isoformat(),
            "input_message": input_message,
            "input_role": "user",
            "output_message": llm_response['output_message'],
            "output_role": output_role,
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "usd_cost": usd_cost,
            "model_name": llm_response.get('model_name', ''),
            "prompt_template": llm_response['prompt_template'],
            "chain_type": llm_response['chain_type'],
            "chat_model": llm_response['chat_model'],
            "vectorstore": llm_response['vectorstore'],
            "temperature": str(llm_response['temperature']),
            "status": status,
            "error_code": error_code,
            "error_message": error_message
        }

        supabase_client.table('messages').insert(message).execute()   