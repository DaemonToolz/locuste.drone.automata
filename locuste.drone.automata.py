# coding=utf-8
# source ~/code/parrot-groundsdk/products/olympe/linux/env/shell à exécuter
# Prévoir : export LD_PRELOAD=/usr/lib/arm-linux-gnueabihf/libatomic.so.1
import sys
# insert at 1, 0 is the script path (or '' in REPL)
import time;
import log.log
import _thread
log.log.init_logs()
log.log.logger.info("Initialisation des logs LOCUSTE")

try : 
    log.log.init_olympe_logs();
    log.log.logger.info("Logger Olympe initialisé")
except (Exception) as error: 
    log.log.logger.error("Une erreur est intervenue") # On reste avec l'affichage standard OLYMPE : Console
    log.log.logger.error("{}".format(error))

import configurations
configurations.load_config()

import drone
all_drones = {}

def associate_drone(data):
    global all_drones
    all_drones[data["ip_address"]] = drone.PyDrone( data["ip_address"],configurations.drone_config["drone_altitude"] )


try :
    for drone_data in configurations.drone_config["drones"]:
        log.log.logger.info("{}".format(drone_data))
        _thread.start_new_thread( associate_drone, (drone_data,))
except (Exception) as error: 
    log.log.logger.error("Une erreur est intervenue")
    log.log.logger.error("{}".format(error))

import signal
def signal_handler(signal, frame):
    global all_drones
    for key in all_drones :
        drone_data = all_drones[key]
        drone_data.Interrupt(None);
        drone_data.ShutDownFailOver();
        drone_data.clear_all();
        time.sleep(1);
        log.log.logger.info("Arrêt et suppression de {}".format(key))
        del key;
        
    all_drones.clear();
    sys.exit(0)
  
signal.signal(signal.SIGINT, signal_handler)
signal.pause()
