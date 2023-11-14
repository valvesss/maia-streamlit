import pinecone
import os

class PineconeClient:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            # Initialize Pinecone
            pinecone.init(api_key=os.getenv("PINECONE_API_KEY"),
                          environment=os.getenv("PINECONE_ENV"))
            cls._instance = pinecone.Index(os.getenv("PINECONE_INDEX"))
        return cls._instance
