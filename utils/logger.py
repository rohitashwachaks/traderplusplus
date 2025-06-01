import logging
import os


def setup_logger(name: str, log_file: str = "./logs/traderplusplus.log", level=logging.INFO) -> logging.Logger:
    """Setup and return a custom logger."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(ch)

        # File handler
        fh = logging.FileHandler(log_file)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)

    return logger
