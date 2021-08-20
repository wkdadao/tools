import logging
import sys

def make_logger(log_path=None, log_level_str='INFO'):
    formatter = logging.Formatter('%(asctime)s: [%(filename)s:%(lineno)d] %(name)s (%(levelname)s): %(message)s')
    if log_path:
        log_handler = logging.FileHandler(log_path)
    else:
        log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(formatter)
    logger = logging.getLogger('socks5_server')
    logger.addHandler(log_handler)
    log_level = logging.getLevelName(log_level_str.upper())
    logger.setLevel(log_level)
    return logger
