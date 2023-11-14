# Built-in modules
import os, time, json, gzip, shutil, requests, asyncio, aiohttp, tempfile

# Local libraries
from maia.src.custom_logging import log_function_execution, logger
from maia.database.s3 import S3Client

s3_client = S3Client().get_instance()

AWS_S3_RAW_FILES_BUCKET = os.getenv("AWS_S3_RAW_FILE_BUCKET")

class Utils(object):
    @log_function_execution
    async def adownload_raw_file(self, download_url: str):
        max_retries=3
        session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=100))    
        for i in range(max_retries):
            try:
                async with session.get(download_url) as response:
                    if response.status != 200:
                        error_message = await response.text()  # get the response text, which might include an error message
                        headers = response.headers  # get the response headers
                        raise Exception(f"Failed to download file: {download_url}. HTTP response: {response.status}, Response body: {error_message}, Headers: {headers}")
                    content = await response.read()
                    return content
            except Exception as e:
                print(f"Error downloading file: {e}. Retry {i + 1} of {max_retries}")
                await asyncio.sleep(1)  # wait before retrying
                
        raise Exception(f"Failed to download file after {max_retries} attempts")

    @log_function_execution
    def download_raw_file(self, download_url: str):
        max_retries = 3
        session = requests.Session()
        for i in range(max_retries):
            try:
                response = session.get(download_url)
                if response.status_code != 200:
                    error_message = response.text  # get the response text, which might include an error message
                    headers = response.headers  # get the response headers
                    raise Exception(f"Failed to download file: {download_url}. HTTP response: {response.status_code}, Response body: {error_message}, Headers: {headers}")
                content = response.content
                return content
            except Exception as e:
                print(f"Error downloading file: {e}. Retry {i + 1} of {max_retries}")
                time.sleep(1)  # wait before retrying
                
        raise Exception(f"Failed to download file after {max_retries} attempts")
    
    @log_function_execution
    def write_raw_file_bytes_to_fs(self, file_name: str, file_data: bytes) -> str:
        # Write binary data to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_name) as tmp:
            tmp.write(file_data)
            tmp_file_name = tmp.name
            
        return tmp_file_name

    @log_function_execution
    def delete_local_file(self, file_path: str) -> None:
        """
        Deletes the specified file if it exists.
        
        :param file_path: Path to the file to be deleted.
        :type file_path: str
        """
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
                print(f'File {file_path} deleted successfully.')
            else:
                print(f'No file found at {file_path}.')
        except Exception as e:
            print(f'An error occurred while deleting the file: {e}')
            
    @log_function_execution
    def move_file_to_s3(self, file_path: str, file_key: str) -> None:
        try:
            s3_client.upload_file(Filename=file_path, 
                                Bucket=AWS_S3_RAW_FILES_BUCKET, 
                                Key=file_key)            
        except Exception as error:
            logger.error(f"API: SOURCES: FILE ({file_key}): failed to write file to s3 | Error: {error}")

    @log_function_execution
    def move_bytes_to_s3(self, bytes: bytes, file_key: str) -> None:
        try:
            s3_client.put_object(Body=bytes, 
                                Bucket=AWS_S3_RAW_FILES_BUCKET, 
                                Key=file_key)
        except Exception as error:
            logger.error(f"API: SOURCES: FILE ({file_key}): failed to write file to s3 | Error: {error}")
                        
    @log_function_execution
    def compress_file(self, input_file_path: str, output_file_path: str) -> None:
        with open(input_file_path, 'rb') as f_in:
            with gzip.open(output_file_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    @log_function_execution
    def compress_dict(self, input_dict: dict) -> bytes:
        
        # Convert the dictionary to JSON string
        json_data = json.dumps(input_dict)

        # Compress the JSON data using gzip
        return gzip.compress(json_data.encode())
    
    @log_function_execution
    def delete_aws_file(self, file_key: str):

        # Delete the object from the specified bucket
        s3_client.delete_object(
            Bucket=AWS_S3_RAW_FILES_BUCKET,
            Key=file_key
        )

    @log_function_execution
    def generate_presigned_upload_url(self, key: str, expiration: int = 3600):
        """
        Generate a presigned URL for uploading a file to AWS S3.
        
        Args:
            key: The name of the object (file) to be uploaded.
            expiration: The expiration time of the presigned URL in seconds. Defaults to 3600 seconds (1 hour).
        
        Returns:
            The presigned URL as a string.
        """
        response = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': AWS_S3_RAW_FILES_BUCKET, 'Key': key},
            ExpiresIn=expiration
        )
        
        return response
    
    @log_function_execution
    def get_aws_download_file_link(self, s3_key: str) -> str:
        # Get presigned url
        url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': AWS_S3_RAW_FILES_BUCKET,
                'Key': s3_key
            },
            ExpiresIn=60 # 5 minutes
        )
        
        return url