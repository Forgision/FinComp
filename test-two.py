from test import get_logger

logger = get_logger("Test")

logger.info("This is an info message.")

def sample_function():
    logger.info("Logging from within a function.")

class SampleClass:
    def __init__(self):
        logger.info("Logging from within a class constructor.")

    def method(self):
        logger.info("Logging from within a class method.")


sample_function()
s = SampleClass()
s.method()