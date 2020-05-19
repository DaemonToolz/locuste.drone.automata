
import json

import log.log


drone_config = {}


def load_config() :
    global drone_config
    log.log.logger.info("Lecture des configurations")

    with open("/home/pi/project/locuste/config/drone_data.json") as f:
        drone_config = json.load(f)

    log.log.logger.info(drone_config)

    log.log.logger.info("Configurations globales chargées")


