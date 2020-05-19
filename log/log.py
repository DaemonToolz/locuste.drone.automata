import logging
import olympe
from pathlib import Path

Path("/home/pi/project/locuste/logs/swarm").mkdir(parents=True, exist_ok=True)
Path("/home/pi/project/locuste/logs/olympe").mkdir(parents=True, exist_ok=True)
Path("/home/pi/project/locuste/stream").mkdir(parents=True, exist_ok=True)


global_format = "%(asctime)s [%(levelname)s] %(name)s - %(funcName)s - %(message)s"
logger = None
drone_log = {}

# Code duplication to remove
# Note: See the notes in GO
def init_logs():
    global logger
    logger = logging.getLogger('locust-agent')
    hdlr = logging.FileHandler('/home/pi/project/locuste/logs/locust-agent-controller.log')
    formatter = logging.Formatter(global_format)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr) 
    logger.setLevel(logging.INFO)
    

def init_logs_for(ip_address):
    global drone_log 
    my_logger = logging.getLogger("locust-agent-{}".format(ip_address))
    hdlr = logging.FileHandler('/home/pi/project/locuste/logs/swarm/locust-agent-{}.log'.format(ip_address))
    formatter = logging.Formatter(global_format)
    hdlr.setFormatter(formatter)
    my_logger.addHandler(hdlr) 
    my_logger.setLevel(logging.INFO)
    drone_log[ip_address] = my_logger

import json
def init_olympe_logs():
    logger.info("[OLYMPE] - Préparation des handlers")

    # On écrase la configuration d'origine d'OLYMPE
    _config = {
        "version": 1,
        "formatters": {
            "default_formatter": {
                "format": (
                    "%(asctime)s [%(levelname)s] %(name)s - %(funcName)s - %(message)s"
                )
            }
        },
        "handlers": {
            "locuste_output": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "/home/pi/project/locuste/logs/olympe/locust-agent-olympe.log",
                "maxBytes": 5120000,
                "backupCount": 5,
                "formatter": "default_formatter",
            }
        },
        "loggers": {
            "olympe": {
                "level": "INFO",
                "handlers": [
                    "locuste_output"
                ]
            }
        },
    }

    logger.info("[OLYMPE] - Préparation des loggers")
    olympe.log.set_config(_config)
    logger.info("[OLYMPE] - Préparation terminée")