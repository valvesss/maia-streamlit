import os
import redis

class Redis():
    def __init__(self):
        """initialize  connection """
        self.connection_url = os.getenv("REDIS_URL")

    def create_connection(self):
        self.connection = redis.from_url(self.connection_url, db=0)

        return self.connection