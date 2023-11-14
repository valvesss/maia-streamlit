# Built-in libraries
import os, base64, requests
from datetime import datetime
from typing import Union
from cryptography.fernet import Fernet
from secrets import token_urlsafe

from postgrest.exceptions import APIError

# Local libraries
from maia.src.stripe_handler import StripeHandler
from maia.src.custom_logging import log_function_execution, logger
from maia.database.supabase import SupabaseClient

supabase_client = SupabaseClient.get_instance()

class User(object):
    @log_function_execution
    def _generate_password(self):
        # Generate a random password
        password = token_urlsafe(16)  # 16 characters long
        
        return password

    @log_function_execution
    def _encrypt_password(self, password: str):
        # Encrypt the password
        encryption_key = os.getenv('PASSWORD_ENCRYPTION_KEY')
        fernet = Fernet(encryption_key)
        encrypted_password = fernet.encrypt(password.encode())
        encoded_encrypted_password = base64.urlsafe_b64encode(encrypted_password).decode('utf-8')
        
        return encoded_encrypted_password
    
    @log_function_execution
    def _decrypt_password(self, encrypted_password: str) -> str:
        encryption_key = os.getenv('PASSWORD_ENCRYPTION_KEY')
        fernet = Fernet(encryption_key)
        decoded_encrypted_password = base64.urlsafe_b64decode(encrypted_password)
        decoded_decrypted_password = fernet.decrypt(decoded_encrypted_password).decode()
        
        return  decoded_decrypted_password
    
    @log_function_execution
    async def _create(self, wix_user: dict) -> Union[dict, bool]:
        
        # Set basic data for create user at supabase
        user_email = wix_user['email']
        user_password = self._generate_password()
        
        # Creates supabase user
        response = supabase_client.auth.sign_up({ "email": user_email, 
                                                "password": user_password })
            
        # Update user at users table   
        user = {}
        user['id'] = response.user.id
        user['email'] = response.user.email
        user['created_at'] = response.user.created_at.isoformat()
        user['_id'] = wix_user['id']
        user['first_name'] = wix_user['first_name']
        user['last_name'] = wix_user['last_name']
        user['status'] = 'active'
        user['subscription_plan_id'] = 1
        user['current_audio_seconds'] = 0
        user['current_files_uploaded'] = 0
        user['current_ai_interactions'] = 0
        user['current_file_bytes_storaged'] = 0
        user['custom_max_interactions'] = 0
        user['custom_max_audio_seconds'] = 0
        user['custom_max_files_uploaded'] = 0
        user['custom_max_file_bytes_storaged']  = 0
        user['has_accepted_privacy_policy'] = False
        user['has_accepted_terms_and_conditions'] = False
        user['password'] = self._encrypt_password(user_password)
        
        # Creates Stripe Account
        user_full_name = wix_user['first_name'] + " " + wix_user['last_name']
        stripe_data = StripeHandler().create_customer(user_email, user_full_name, response.user.id)
        if stripe_data:
            user['stripe_customer_id'] = stripe_data['id']
        else:
            user['stripe_customer_id'] = None
            
        # Insert new user
        supabase_client.table('users').insert(user).execute()
        
        user['session_jwt'] = response.session.access_token
        
        return user

    @log_function_execution
    def get_user_subscription_status(self, user_id: str) -> str:
        response = supabase_client.table('users').select('stripe_subscription_id').eq('id', user_id).execute()
        if response.data:
            subscription_id = response.data[0]['stripe_subscription_id']
            subscription_status = StripeHandler().get_subscription_status(subscription_id)
            return subscription_status
        else:
            return None
    
    @log_function_execution
    def get_user_max_ai_interactions(self, subscription_plan_id: int, custom_max_interactions: int) -> int:
        plan_name = f"SUB_PLAN_{subscription_plan_id}_MAX_AI_INTERACTIONS"
        plan_max_ai_interactions = int(os.getenv(plan_name))
        
        # Get the maximum of custom_max_interactions and plan_max_ai_interactions
        return max(plan_max_ai_interactions, custom_max_interactions)
    
    @log_function_execution
    def get_user_current_monthly_ai_interactions(self, user_id: str) -> Union[int, None]:
        # Get the current date
        now = datetime.now()
        
        # Format the current date as YYYY-MM-01
        current_month_year = now.strftime('%Y-%m-01')
        
        response = supabase_client.table('monthly_user_interactions') \
                                  .select('interactions_count') \
                                  .eq('user_id', user_id) \
                                  .eq('month_year', current_month_year) \
                                  .execute()
        
        if response.data:
            return response.data[0]['interactions_count']
        return None
    
    @log_function_execution
    def get_user_current_monthly_usage(self, user_id: str) -> Union[int, None]:
        # Get the current date
        now = datetime.now()
        
        # Format the current date as YYYY-MM-01
        current_month_year = now.strftime('%Y-%m-01')
        
        response = supabase_client.table('monthly_user_interactions') \
                                  .select('*') \
                                  .eq('user_id', user_id) \
                                  .eq('month_year', current_month_year) \
                                  .execute()
        
        if response.data:
            return response.data[0]
        return None
    
    @log_function_execution
    def add_invoice(self, session: dict) -> None:
        """
        Add user's checkout session data as an Invoice object.
        
        args:
            session (dict): Stripe's checkout session object
        """
        # Convert UNIX epoch timestamps to ISO 8601 format
        created_at = datetime.utcfromtimestamp(session['created']).isoformat()
        expires_at = datetime.utcfromtimestamp(session['expires_at']).isoformat()
        
        # Extract useful information from session
        invoice = {
            'id': session['invoice'],
            'total_amount': session['amount_total'],
            'currency': session['currency'],
            'customer_id': session['customer'],
            'customer_email': session['customer_details']['email'],
            'payment_status': session['payment_status'],
            'subscription_id': session['subscription'],                
            'session_id': session['id'],
            'created_at': created_at,
            'expires_at': expires_at,
            'success_url': session['success_url'],
            'product_id': session['metadata']['product_id']
        }
        
        supabase_client.table('invoices').insert(invoice).execute()
        
    @log_function_execution
    def _approve_consent(self, user_id: str):
        response = supabase_client.table('users') \
                                .update({'has_accepted_terms_and_conditions': True,
                                         'has_accepted_privacy_policy': True}) \
                                .eq('id', user_id) \
                                .execute()
        
    @log_function_execution
    def _get_by_email(self, email: str) -> Union[dict, None]:
        # Get user
        response = supabase_client.table('users').select('*').eq("email", email).execute()
    
        if response.data:
            user = response.data[0]
            return user
        return None

    @log_function_execution
    def _get_by_id(self, user_id: str) -> Union[dict, None]:
        # Get user
        response = supabase_client.table('users').select('*').eq("id", user_id).execute()
    
        if response.data:
            user = response.data[0]
            return user
        return None                

    @log_function_execution
    def _get_by_wix_id(self, user_wix_id: str) -> Union[dict, None]:
        # Get user
        response = supabase_client.table('users').select('*').eq("_id", user_wix_id).execute()
    
        if response.data:
            user = response.data[0]
            return user
        return None      
    
    @log_function_execution
    async def _log_in(self, user: dict):
        
        decrypted_password = self._decrypt_password(user['password'])
        response = supabase_client.auth.sign_in_with_password({ "email": user['email'], 
                                                              "password": decrypted_password })
        return response.session.access_token
    
    @log_function_execution
    async def refresh_wix_session(self, user_wix_id: str) -> dict:
        
        user = self._get_by_wix_id(user_wix_id)
        session_jwt = await self._log_in(user)
            
        # Hangs connection due to supabase python class bug
        # https://github.com/supabase-community/supabase-py/issues/494
        supabase_client.auth.sign_out()
        
        return session_jwt
    
    @log_function_execution
    def increment_user_current_file_bytes_storaged(self, user_id: str, increment_value: int):
        try:
            supabase_client.rpc(
                            "increment_user_current_file_bytes_storaged", 
                            {"user_id": user_id, "increment_value": increment_value}
                            ).execute()
        except APIError as error:
            logger.error(f"APIError: FAILED: increment_user_current_file_bytes_storaged | Error: {error}")
            pass

    @log_function_execution
    def decrement_user_current_file_bytes_storaged(self, user_id: str, decrement_value: int):
        try:
            supabase_client.rpc(
                            "decrement_user_current_file_bytes_storaged", 
                            {"user_id": user_id, "decrement_value": decrement_value}
                            ).execute()
        except APIError as error:
            logger.error(f"APIError: FAILED: decrement_user_current_file_bytes_storaged | Error: {error}")
            pass
        
    @log_function_execution
    def increment_user_current_ai_interactions(self, user_id: str):
        supabase_client.rpc(
                        "increment_user_current_ai_interactions", 
                        {"p_user_id": user_id}
                    ).execute()

    @log_function_execution
    def increment_user_monthly_ai_interactions(self, user_id: str):
        supabase_client.rpc(
                        "increment_user_monthly_ai_interactions", 
                        {"p_user_id": user_id}
                    ).execute()
        
    @log_function_execution
    def increment_user_monthly_audio_seconds(self, user_id: str, audio_seconds: int):
        try:
            supabase_client.rpc(
                            "increment_user_monthly_audio_seconds", 
                            {"p_user_id": user_id, "p_seconds": audio_seconds}
                        ).execute()
        except APIError as error:
            logger.error(f"APIError: FAILED: increment_user_current_file_bytes_storaged | Error: {error}")
            pass

    @log_function_execution
    def increment_user_current_files_uploaded(self, user_id: str):
        try:
            supabase_client.rpc(
                            "increment_user_current_files_uploaded", 
                            {"p_user_id": user_id}
                        ).execute()
        except APIError as error:
            logger.error(f"APIError: FAILED: increment_user_current_file_bytes_storaged | Error: {error}")
            pass

    @log_function_execution
    def decrement_user_current_files_uploaded(self, user_id: str):
        supabase_client.rpc(
                        "decrement_user_current_files_uploaded", 
                        {"p_user_id": user_id}
                    ).execute()
    