import sys
import traceback

from logger.custom_logger import CustomLogger
logger=CustomLogger().get_logger(__file__)

class DocumentPortalException(Exception):
    """Custom exception for Document Portal"""
    def __init__(self, error_message, error_details=None):
        super().__init__(error_message)
        self.error_message = str(error_message)
        
        # If error_details is None, get current exception info
        if error_details is None:
            error_details = sys
        
        # Get exception info
        exc_type, exc_value, exc_tb = error_details.exc_info()
        
        if exc_tb is not None:
            self.file_name = exc_tb.tb_frame.f_code.co_filename
            self.lineno = exc_tb.tb_lineno
            self.traceback_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        else:
            # Fallback when no exception is active
            self.file_name = "unknown"
            self.lineno = 0
            self.traceback_str = "No traceback available"
        
    def __str__(self):
       return f"""
        Error in [{self.file_name}] at line [{self.lineno}]
        Message: {self.error_message}
        Traceback:
        {self.traceback_str}
        """
    
if __name__ == "__main__":
    try:
        # Simulate an error
        a = 1 / 0
        print(a)
    except Exception as e:
        app_exc=DocumentPortalException(e,sys)
        logger.error(app_exc)
        raise app_exc