import os
from supabase import create_client, Client

from maia.src.custom_logging import log_function_execution, logger

class SupabaseClient:
    _instance: Client = None
    
    @classmethod
    def get_instance(cls) -> Client:
        if cls._instance is None:
            url: str = os.environ.get("SUPABASE_URL")
            key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            cls._instance = create_client(url, key)
        return cls._instance
    
    @log_function_execution
    def update(self, table: str, id: str, object: dict) -> None:
        client = self.get_instance()
        try:
            client.table(table).update(object).eq('id', id).execute()
        except Exception as e:
            logger.error(f"SupabaseClient.update ERROR: {e}\nDetails: table: {table} | id: {id} | object: {object}")