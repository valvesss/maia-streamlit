# Local libraries
import os
from uuid import uuid4
from typing import Union
from datetime import datetime

# 3rd part libraries
import stripe
from stripe.error import StripeError, InvalidRequestError

# Local libraries
from maia.src.custom_logging import log_function_execution, logger
from maia.database.supabase import SupabaseClient

supabase_client = SupabaseClient.get_instance()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STARTER_PRICE_ID = os.getenv("STRIPE_SUB_STARTER_PRICE_ID")
STARTER_PRODUCT_ID = os.getenv("STRIPE_SUB_STARTER_PRODUCT_ID")

class StripeHandler(object):
    
    @log_function_execution
    def assign_subscription(self, session: dict) -> None:
        """
        Update user's plan given the Stripe checkout session.
        
        args:
            session (dict): Stripe's checkout session object
        """
        # Assign plan to user
        try:
            supabase_client.table('users') \
                            .update({'stripe_subscription_id': session['subscription'],
                                     'subscription_plan_id': int(session['metadata']['plan_id'])}) \
                            .eq('id', session['metadata']['user_id']) \
                            .execute()
        except Exception as e:
            logger.error(f"Error trying to assign_subscription: {e}")

    @log_function_execution
    def assign_trial_subscription(self, session: dict) -> None:
        """
        Update user's plan given the Stripe checkout session.
        
        args:
            session (dict): Stripe's checkout session object
        """
        subscription = session['items']['data'][0]
        subscription_id = subscription['subscription']
        product_id = subscription['plan']['product']
        
        if product_id == STARTER_PRODUCT_ID:
            plan_id = 1
        
        try:
            supabase_client.table('users') \
                            .update({'stripe_subscription_id': subscription_id,
                                     'subscription_plan_id': plan_id}) \
                            .eq('stripe_customer_id', session['customer']) \
                            .execute()
        except Exception as e:
            logger.error(f"Error trying to assign_subscription: {e}")
                 
    @log_function_execution
    def cancel_subscription(self, session: dict) -> None:
        """
        Update user's plan given the Stripe checkout session.
        
        args:
            session (dict): Stripe's checkout session object
        """
        try:
            supabase_client.table('users') \
                           .update({'stripe_subscription_id': None,
                                    'subscription_plan_id': 0}) \
                           .eq('stripe_customer_id', session['customer']) \
                           .execute()
        except Exception as e:
            logger.error(f"Error trying to cancel_subscription: {e}")
        
    @log_function_execution
    def get_subscription_status(self, subscription_id: str) -> Union[dict, None]:
        try:
            response = stripe.Subscription.retrieve(subscription_id)
            status = response['status']
            return status
        except InvalidRequestError:
            return None
        except Exception:
            return None
        
    @log_function_execution
    def create_starter_subscription(self, customer_id: str, user_id: str) -> Union[str, None]:
        """
        Creates Subscription Checkout Page attached to user email and ID.
        
        args:
            customer_id (str): Stripe's customer ID
            
        return:
            checkout_page (str): succesfull checkout page url
            None: in case of any error
        
        """
        try:
            checkout_session = stripe.checkout.Session.create(
                customer = customer_id,
                payment_method_types = ['card'],
                line_items = [
                    {
                        'price': STARTER_PRICE_ID,
                        'quantity': 1,
                    },
                ],
                metadata = {
                            'product_id': STARTER_PRODUCT_ID,
                            'price_id': STARTER_PRICE_ID,
                            'user_id': user_id,
                            'plan_id': 1
                           },
                mode = 'subscription',
                success_url = 'https://ninev.co/files',
                cancel_url = 'https://ninev.co/plans',
                subscription_data = {
                    "trial_settings": {
                            "end_behavior": {
                                "missing_payment_method": "pause"
                            }
                    },
                    "trial_period_days": 3,
                },
                payment_method_collection = "always",
            )
            checkout_url = checkout_session.url
            return checkout_url
        except StripeError as e:
            logger.error(f"failed to create checkout page for customer {customer_id}, error: {e}")
            return None
        
    @log_function_execution
    def get_no_login_billing_page_url(self, customer_id: str):
        
        response = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url="https://ninev.co/files"
        )
        
        return response['url']
    
    @log_function_execution
    def create_customer(self, email: str, name: str, user_id: str) -> Union[dict, None]:
        """
        Creates Stripe Customer with email.
        Email is not a unique key for stripe, so it can duplicate accounts.
        
        args:
            email (str): new customer email
            name (str): new customer full name
        
        return:
            customer (dict): if success, dict with customer data
            None: in case of any error from Stripe
        
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata= {'user_id': user_id}
            )
            return customer
        except StripeError as e:
            logger.error(f"could not create Stripe customer: {e}")
            return None