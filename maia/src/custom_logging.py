# Built-in libraries
import asyncio, logging, functools, inspect

# Configure the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_function_execution(func):
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        class_name = args[0].__class__.__name__ if args and inspect.ismethod(func) else ''
        logger.info(f"{class_name}.{func.__name__} started" if class_name else f"{func.__name__} started")
        result = await func(*args, **kwargs)
        logger.info(f"{class_name}.{func.__name__} finished" if class_name else f"{func.__name__} finished")
        return result            
        
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        class_name = args[0].__class__.__name__ if args and inspect.ismethod(func) else ''
        logger.info(f"{class_name}.{func.__name__} started" if class_name else f"{func.__name__} started")
        result = func(*args, **kwargs)
        logger.info(f"{class_name}.{func.__name__} finished" if class_name else f"{func.__name__} finished")
        return result
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

