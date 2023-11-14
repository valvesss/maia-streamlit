# Built-in modules
import os
from uuid import uuid4
from datetime import datetime

# 3rd part Modules
import openai
from langchain.chains import RetrievalQA
from langchain.vectorstores import Pinecone
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.callbacks import get_openai_callback
from langchain.embeddings import OpenAIEmbeddings

# Local libraries
from maia.src.custom_logging import log_function_execution, logger
from maia.src.message import Message
from maia.src.prompt_templates import template_br_1, template_br_2
from maia.src.user import User
from maia.database.supabase import SupabaseClient

# Initialize Supabase
supabase_client = SupabaseClient.get_instance()

# Set OpenAIEmbeddings
embeddings = OpenAIEmbeddings()

MODEL_NAME_4K = "gpt-3.5-turbo-0613"
MODEL_NAME_16K = "gpt-3.5-turbo-16k-0613"
CHAIN_TYPE = "stuff"
PROMPT_TEMPLATE = template_br_2
CHAT_MODEL = "ChatOpenAI"
VECTORSTORE = "pinecone"
TEMPERATURE = 0.1

@log_function_execution
def get_docs_from_vector_db(index_name: str, namespace: str):
    return Pinecone.from_existing_index(embedding=embeddings, index_name=index_name, namespace=namespace)

@log_function_execution
def create_llm_chain(model_name: str = MODEL_NAME_4K):
    llm = ChatOpenAI(model_name=model_name, temperature=TEMPERATURE)
    
    return llm

@log_function_execution
def get_chain_prompt_template():
    PROMPT = PromptTemplate(
        template=PROMPT_TEMPLATE, input_variables=["context", "question"]
    )
    
    chain_type_kwargs = {"prompt": PROMPT}
    
    return chain_type_kwargs

@log_function_execution
def get_retrieval_qa(llm, docsearch, chain_type_kwargs):
    qa = RetrievalQA.from_chain_type(llm=llm, 
                                     chain_type=CHAIN_TYPE, 
                                     retriever=docsearch.as_retriever(),
                                     chain_type_kwargs=chain_type_kwargs)
    
    return qa    

@log_function_execution
def query_llm_chain_with_callback(llm, docsearch, chain_type_kwargs: dict, query: str) -> dict:
    def run_query(llm_model, model_name):
        response = {
            'error': False,
            'model_name': model_name,
            'output_message': None,
            'openai_callback': None,
            'error_code': None,
            'error_message': None,
            'chain_type': CHAIN_TYPE,
            'prompt_template': PROMPT_TEMPLATE,
            'vectorstore': VECTORSTORE,
            'temperature': TEMPERATURE,
            'chat_model': CHAT_MODEL,
        }
        qa = get_retrieval_qa(llm_model, docsearch, chain_type_kwargs)
        try:
            with get_openai_callback() as cb:
                openai_response = qa.run(query)
                response.update({
                    'output_message': openai_response,
                    'openai_callback': cb
                })
        except openai.InvalidRequestError as error:
            logger.warn(f'Message Length Exceed, using {model_name}.')
            response.update({
                'error': True,
                'error_code': error.code,
                'error_message': error
            })
        except Exception as error:
            logger.error(f"OpenAI: {model_name}: failed to query ERROR: {error}")
            response.update({
                'error': True,
                'error_message': error
            })
        return response

    response_4k = run_query(llm, MODEL_NAME_4K)
    if response_4k['error'] and response_4k['error_code'] == 'context_length_exceeded':
        logger.warn("Previous message exceed 4K context, using 16K model")
        llm_16k = create_llm_chain(MODEL_NAME_16K)
        response_16k = run_query(llm_16k, MODEL_NAME_16K)
        return response_16k

    return response_4k

@log_function_execution
def query(namespace: str, query: str) -> dict:
    vectorstore = get_docs_from_vector_db(os.getenv('PINECONE_INDEX'), namespace)
    llm = create_llm_chain()
    chain_type_kwargs = get_chain_prompt_template()
    llm_response = query_llm_chain_with_callback(llm, vectorstore, chain_type_kwargs, query)
    return llm_response
        
