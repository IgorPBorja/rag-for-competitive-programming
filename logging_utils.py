import logging


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # add function name to logging too
    ch = logging.StreamHandler()
    # attributes for string formatting are taken from LogRecord attrs
    format_string = """
        %(asctime)s - %(levelname)s - %(pathname)s.%(funcName)s:%(lineno)s - %(message)s
    """.strip()
    ch.setFormatter(logging.Formatter(format_string))
    logger.addHandler(ch)
    return logger
