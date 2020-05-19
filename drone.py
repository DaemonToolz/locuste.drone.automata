import sys
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, './log')
sys.path.insert(1, './listeners')

import log.log

# Note: Refactoring to be done
# Update names, consolidate the global process, add security and fail-overs
# Upgrades to be done after Real-life test
# Separate Common Section into Automated & Manual to avoid overlap


#region Drone SDK
import olympe

from reapeated_timer import RepeatedTimer
from olympe.enums.ardrone3.Piloting import MoveTo_Orientation_mode
from olympe.enums.ardrone3.PilotingState import FlyingStateChanged_State
from olympe.messages.ardrone3.Piloting import TakeOff, Landing, moveTo, NavigateHome,CancelMoveTo, moveBy

from olympe.messages.common.CommonState import BatteryStateChanged

import olympe.messages.ardrone3.GPSSettingsState

from olympe.messages.ardrone3.PilotingState import (
    PositionChanged,
    AlertStateChanged,
    FlyingStateChanged,
    NavigateHomeStateChanged,
    moveToChanged
)
from olympe.messages.ardrone3.GPSSettingsState import GPSFixStateChanged

#endregion Drone SDK

#region Web
import socketio
import json
#endregion Web 

#region Video
from olympe.messages import gimbal
#endregion Video

#region threading
import queue
import time
import threading
#endregion threading

#region automaton
from drone_commands.commands import PublicCommands, DroneCommandParams, DroneCommand, CommandAbordException
from localisation.coordinates import DroneHomeRelay, DroneCoordinates

drone_global_commands = {}
from listeners.flightListener import FlightListener
#endregion automaton


#192.168.42.1
class PyDrone(object):
    #region Gestionnaire de drone
    def __init__(self, ip_adress, min_height):
        """
            PyDrone encapsule le FlightListener et le OLYMPE.Drone
            Gère l'intégralité des états et des connexions vers l'unité de contrôle
        """
        global drone_global_commands

        log.log.init_logs_for(ip_adress)
        self.__init_variables()
        
        self._my_ip = ip_adress
        self.my_name = "ANAFI_{}".format(self._my_ip)
        drone_global_commands[self._my_ip] = { 
            "error_queue": queue.Queue(),
            "on_error": False,
            "ongoing": True,
            "successful_attempts": 0,
            "camera_pitch":0.0
        }

        threading._start_new_thread( self.error_queue_handler, ())

        self._drone_min_height = min_height;
        self._ws_port = 7000 + int(self._my_ip.split(".")[2])
        self._relay = DroneHomeRelay() 

        self._drone_coordinates = DroneCoordinates()


        self.my_log.info("Initialisation du drone {} à une altiltute minimale de vol de {}".format(ip_adress, min_height))
        self.__init_socket_streaming()
        self.update_status();   # Premier set de mises à jours
        self.__initialize()
        
        if not self._initialized : 
            self._retry_init = RepeatedTimer(1, self.__initialize)

    def __init_variables(self): 
        self._retry_init = None
        self._reconnect_timer = None;
        self._online_output = None
        self._on_test = False;
        self._manual_unit = False
        self._connected = False
        self._initialized = False
        self._failure_count = 0
        self._max_retry = 5

    def __initialize(self):
        try : 
            self.my_log.info("Tentative de création de la connexion au drone {}".format(self._my_ip))
            self._drone = olympe.Drone(self._my_ip, media_autoconnect=False)
            self.my_log.info("Création du système d'écoute {}".format(self._my_ip))
            self.__init_listener();
            self.my_log.info("Status du drone : OK")
            if self._retry_init is not None :
                self._retry_init.stop()
            self._retry_init = None

            self._initialized = True
            self.__reconnect()

            if not self._connected :
                self._reconnect_timer = RepeatedTimer(1, self.__reconnect)

        except(Exception) as ex:
            self.my_log.error("Status du drone : ERREUR, tentative de création de flux")
            self.my_log.error(ex)
            
            self._initialized = False
        self.update_status();

    def __reconnect(self):
        try :
            self.my_log.info("Tentative de connexion au drone {}".format(self._my_ip))
            
            self._drone.connect()
            #self._drone(GPSFixStateChanged(_policy = 'wait'))
            self.my_log.info("Récupération des coordonnées pour {}".format(self._my_ip))
            self._drone_orientation = 0;
            self._connected = True
            if self._reconnect_timer is not None : 
                self._reconnect_timer.stop()

            self._reconnect_timer = None;
            
            self.__init_video_streaming()
            self._brain_client.emit('internal_status_changed', {"id":self.my_name, "status":"BatteryStateChanged", "result": self._drone.get_state(BatteryStateChanged)["percent"]})
        
        except(Exception) as ex :
            self.my_log.error("Echec de la connexion au drone {}".format(self._my_ip))
            self._connected = False
            self.my_log.error(ex)
        self.update_status();
   
    def __init_listener(self):
        try : 
            self._flight_listener = FlightListener(self._drone) 
            self._flight_listener.set_logger(self.my_log)
            self._flight_listener.set_my_name(self.my_name)
            self._flight_listener.set_relay(self._relay)
            self._flight_listener.set_socket(self._brain_client);
            self._flight_listener.set_initialized_socket(self._socket_initialized)
            self._flight_listener.set_drone_coordinates(self._drone_coordinates)
            self._flight_listener.on_signal_lost(self.Interrupt);
            self._flight_listener.subscribe();
            
        except(Exception) as error: # On a planté au niveau du subscribe
            self.my_log.error(error)

    def __init_socket_streaming(self):

        try :
            self._brain_client = socketio.Client() 
           
            self._brain_client.on('connect', self.connect)
            self._brain_client.on('connect_error', self.connect_error)
            self._brain_client.on('disconnect', self.disconnect)
            self._brain_client.on('request_manual', self.RequestManualFlight)
            self._brain_client.on('request_automatic', self.RequestAutomaticFlight)
            self._brain_client.on('request_emergency_disconnect', self.RequestEmergencyDisconnect)
            self._brain_client.on('request_emergency_reconnect', self.RequestEmergencyReconnect)

            self._brain_client.on('request_simulation', self.EnterTestingMode)
            self._brain_client.on('request_normal', self.LeaveTestingMode)

            self._brain_client.on('identify_operator', self.OnNewOperator)
            self._brain_client.on('interrupt', self.Interrupt)
            
            self._brain_client.on('command', self.SendCommand)
            
            self._brain_client.connect('ws://localhost:21000',transports=["websocket"] )

            if hasattr(self, "_flight_listener"):
                self._flight_listener.set_socket(self._brain_client);
            
            self.socket_initialized = True
        except(Exception) as ex :
            self.my_log.error("Echec de la connexion au drone {}".format(self._my_ip))
            self.socket_initialized = False
            self.my_log.error(ex);


    def EnterTestingMode(self, data):
        self.my_log.warning("Activation du mode test / simulation")
        self._on_test = True;
        self.update_status()
        
    def LeaveTestingMode(self, data):
        self._on_test = False;
        self.my_log.warning("Fin du mode test / simulation")
        self.update_status()
        
    def RequestManualFlight(self, data):
        self._manual_unit = True;
        self.my_log.warning("Passage en mode vol Manuel")
        self.update_status()
        
    def OnNewOperator(self, data):
        self._brain_client.emit('acknowledge', {"name":self.my_name}) # Deux étapes : d'abord un acknowledge suivi de la position actuelle
        if self._connected and self._initialized:
            self._brain_client.emit('position_update', {"id":self.my_name, "position": self._drone.get_state(PositionChanged)})            

    def RequestAutomaticFlight(self, data):
        self.my_log.warning("Passage en mode vol Automatique")
        self._manual_unit = False;
        if self._connected and self._initialized:
            self.AutomaticSetCameraDown();
        self.update_status()

    def RequestEmergencyDisconnect(self, data): 
        self.my_log.warning("Déconnexion de l'automate")
        if self._connected and self._initialized: 
            self._flight_listener.unsubscribe()
            self._drone.disconnect();
            self._connected = False
            self.update_status()

    def RequestEmergencyReconnect(self, data):
        self.my_log.warning("Reconnexion à l'automate")
        if not self._connected and self._initialized: 
            self._flight_listener.subscribe()
            self._drone.connect()
            self._connected = True
            self.update_status()

    def Interrupt(self, data):
        self.my_log.warning("Interruption généralisée")
        self.my_log.warning("Remise à zéro de l'état de la caméra")
        self.CommonSetStandardCamera();
        self.my_log.warning("Passage en mode manuel du drone")
        self.RequestManualFlight(data);
        self.my_log.warning("Déconnexion du drone")
        self.RequestEmergencyDisconnect(data);
        self.update_status()


    def ShutDownFailOver(self):
        self.my_log.warning("Arrêt des processus de failover")
        self.ongoing = False
        
    #endregion Gestionnaire de drone
    #region Gestionnaire de commandes
   
    def SendCommand(self, command):
        if not self._on_test and (not self._connected or not self._initialized) :
            return; 

        name = "";#command.name;
        params = None; #command.params

        # Commandes envoyées directement par le programme Python
        if isinstance(command, DroneCommand):
            name = "{}{}".format(command.command_type.value,command.name.value);
            params = command.params
        # Commandes envoyées par WebSocket
        elif isinstance(command, dict):
            name = str(command["name"])
            params = command["params"] if "params" in command.keys() else None
        else :
            self.my_log.error("Mauvaise informations envoyées, aucune interpretation de la commande")
            return;

        try :
            target = getattr(self, name)
            try :

                self.my_log.info("Commande {} reçue, tentative de traitement".format(name, self._failure_count))
                if self.on_error or not self.error_queue.empty(): # pour éviter de bypasser les autres appels
                    self.error_queue.put({"function": target, "params": params})
                else : 
                    if params is not None:
                        target(params);
                    else :
                        target()
                    self._failure_count = 0
            except(Exception) as error: 
                self._failure_count += 1
                self.my_log.warning("Commande {} non reçue, tentative #{}".format(name, self._failure_count))
                self.my_log.error("Détail de l'erreur pour {} ".format(name))
                self.my_log.error("Trace : {}".format(error))
                # On sanctionne tous les échecs
                if self._failure_count >= self._max_retry :
                    raise CommandAbordException()
                time.sleep(1)
                self.SendCommand(command);
        except (CommandAbordException) :
            self.my_log.error("{} échecs, abandon et transfert de la commande {}".format(self._failure_count, name))
            self._failure_count = 0
            self._on_error = True
        except (Exception) as any_error: 
            self.my_log.error("Commande {} non trouvée : {}".format(name, any_error))
        

    def error_queue_handler(self):
        result_ok = False;
        while self.ongoing :
            result_ok = False;
            if not self.on_error and self.error_queue.empty():
                time.sleep(0.05)
                self.successful_attempts = 0 ;
                continue;
            try :
                call = self.error_queue.get()
                funcion = call["function"]
                params = call["params"] if "params" in call.keys() else None
                
                while not result_ok :
                    try : 
                        if params is not None:
                            funcion(params);
                        else :
                            funcion()
                        self._failure_count = 0
                        result_ok = True;
                        self.successful_attempts = self.successful_attempts+1
                    except(Exception) as error: 
                        self._failure_count += 1
                        self.my_log.warning("Commande non reçue, tentative #{}".format(self._failure_count))
                        self.my_log.error("Détail de l'erreur")
                        self.my_log.error("Trace : {}".format(error))
                        # On sanctionne tous les échecs et on passe la commande
                        if self._failure_count >= self._max_retry :
                            break;
                        time.sleep(0.05)

                if not result_ok : 
                    self.my_log.warning("Echec de la commande précédent, passage à la commande suivante")

                if self.successful_attempts >= self._max_retry : 
                    self.on_error = False;

            except(Exception) as queue_error : 
                self.my_log.error(queue_error)
        self.update_status()
    #endregion Gestionnaire de commandes

    #region Comportement autonomes
    def AutomaticGoTo(self,coordinates):
        if isinstance(coordinates, dict):
            coordinates = DroneCommandParams(**coordinates)

        if not self._manual_unit :
            if not self._on_test:
                self._drone(
                    moveTo(coordinates.latitude,coordinates.longitude,self._drone_coordinates.altitude, MoveTo_Orientation_mode.TO_TARGET )
                    >> FlyingStateChanged(state="hovering", _timeout=5)
                    ).wait()
            else :
                self.my_log.info("Mode simulation: informations reçues {} ".format(coordinates.to_string()))
                time.sleep(1)
            self._brain_client.emit('on_command_success', {"name":self.my_name})
        else : 
            self.my_log.info("Mode Manuel : Commande ignorée")  
   
    def AutomaticCancelGoTo(self):
        if not self._manual_unit :
            if not self._on_test:
                self._drone(CancelMoveTo()).wait()
            else :
                self.my_log.info("Mode simulation: informations reçues")
                time.sleep(1)
            self._brain_client.emit('on_command_success', {"name":self.my_name})
        else : 
            self.my_log.info("Mode Manuel : Commande ignorée")  
    
    def AutomaticSetCameraDown(self):
        if not self._manual_unit :
            if not self._on_test:
            
                self._drone(gimbal.set_target(
                    gimbal_id=0,
                    control_mode="position",
                    yaw_frame_of_reference="none",
                    yaw=0.0,
                    pitch_frame_of_reference="absolute",
                    pitch=-1,
                    roll_frame_of_reference="none",
                    roll=0.0,
                )).wait()
                self.camera_pitch = -1;
                
            else :
                self.my_log.info("Mode simulation: informations reçues")
            self._brain_client.emit('on_command_success', {"name":self.my_name})
        else : 
            self.my_log.info("Mode Manuel : Commande ignorée")  
    #endregion Comportement autonomes

    #region Comportement autonomes / manuels
    def CommonSetStandardCamera(self):
        if not self._on_test:
            self._drone(gimbal.set_target(
                    gimbal_id=0,
                    control_mode="position",
                    yaw_frame_of_reference="none",
                    yaw=0.0,
                    pitch_frame_of_reference="absolute",
                    pitch=0,
                    roll_frame_of_reference="none",
                    roll=0.0,
                )).wait()
            self.camera_pitch = 0;
        else :
            self.my_log.info("Mode simulation: informations reçues")


    def CommonGoHome(self):
        if not self._on_test:
            self.CommonSetStandardCamera()
            try :
                self._drone(NavigateHome(1)).wait() # On capture l'erreur si le drone est trop près pour activer "NavigateHome" 
            except(Exception) as error : 
                self.my_log.warning(error)

            try : 
                self._drone(Landing()).wait() # On se considère assez proche pour l'atterissage
            except(Exception) as error:
                self.my_log.warning(error)

        else :
            self.my_log.info("Mode simulation: informations reçues")

    def CommonTakeOff(self):
        if not self._on_test:
            if (self._drone.get_state(FlyingStateChanged)["state"] is not FlyingStateChanged_State.hovering):
                 self._drone(GPSFixStateChanged(fixed=1, _timeout=10, _policy="check_wait")).wait()
                 self._drone( TakeOff(_no_expect=True) & FlyingStateChanged(state="hovering", _policy="wait", _timeout=5) ).wait()
           
        else :
            self.my_log.info("Mode simulation: informations reçues")

    #endregion Comportement autonomes

    #region Comportement  manuel
    def ManualMove(self,params):
        if isinstance(params, dict):
            params = DroneCommandParams(**params)
        if self._manual_unit :
            if not self._on_test:
                self._drone(moveBy(params.x,params.y,params.z,params.orientation))
            else :
                self.my_log.info("Mode simulation: informations reçues {} ".format(params.to_string()))
        else :
            self.my_log.info("Mode automatique : commande {} ignorée ".format(params.to_string()))


    def ManualTiltCamera(self,params):
        if isinstance(params, dict):
            params = DroneCommandParams(**params)
        if self._manual_unit :
            if not self._on_test:
                self._drone(gimbal.set_target(
                    gimbal_id=0,
                    control_mode="position",
                    yaw_frame_of_reference="none",
                    yaw=0.0,
                    pitch_frame_of_reference="absolute",
                    pitch=self.camera_pitch+params.pitch,
                    roll_frame_of_reference="none",
                    roll=0.0,
                )).wait()
                self.camera_pitch = self.camera_pitch +params.pitch
            else :
                self.my_log.info("Mode simulation: informations reçues {} ".format(params.to_string()))
        else :
            self.my_log.info("Mode automatique : commande {} ignorée ".format(params.to_string()))

    #endregion Comportement manuel

    #region Sections héritées
    def __enter__(self):
        """ A utiliser avec le with """
        return self

    def __del__(self):
        """ A utiliser avec le with """
        pass;
    #endregion Sections héritées
    
    #region Sections messages et événements
    def clear_all(self):      
        self.Interrupt(None);
        
        self.socket_initialized = False;
        self._camera_initialized = False;
        self._connected = False;
        self._manual_unit = False;
        self._initialized = False;
        self._on_test = False;

        if self._retry_init is not None :
            self._retry_init.stop()
        self._retry_init = None;

        if self._reconnect_timer is not None :
            self._reconnect_timer.stop()
        self._reconnect_timer = None;

        try: 
            if self._flight_listener is not None: 
                self._flight_listener.unsubscribe()
        except(Exception) as error: 
            self.my_log.warning(error)

        self._flight_listener = None;

        if  self._socket_initialized :
            self._brain_client.disconnect()

        time.sleep(1);
        self.update_status()

    def update_status(self):
        updated_data =  {
            "on_error": self.on_error,
            "ongoing": self.ongoing,
            "connected": self._connected,
            "initialized": self._initialized,
            "sim": self._on_test,
            "manual": self._manual_unit
        }
        with open('/home/pi/project/locuste/data/{}.json'.format(self.my_name), 'w') as f:
            json.dump(updated_data, f)

    #endregion Sections messages et événements

    #region Aliases
    @property
    def my_log(self): 
        return log.log.drone_log[self._my_ip]
    
    @property
    def on_error(self): 
        global drone_global_commands
        return drone_global_commands[self._my_ip]["on_error"]

    @on_error.setter
    def on_error(self, value): 
        global drone_global_commands
        drone_global_commands[self._my_ip]["on_error"] = value
        
        
    @property
    def error_queue(self): 
        global drone_global_commands
        return drone_global_commands[self._my_ip]["error_queue"]

    
    @property
    def ongoing(self): 
        global drone_global_commands
        return drone_global_commands[self._my_ip]["ongoing"]

    @ongoing.setter
    def ongoing(self, value): 
        global drone_global_commands
        drone_global_commands[self._my_ip]["ongoing"] = value


    @property
    def successful_attempts(self):
        global drone_global_commands
        return drone_global_commands[self._my_ip]["successful_attempts"]

    @successful_attempts.setter
    def successful_attempts(self, value): 
        global drone_global_commands
        drone_global_commands[self._my_ip]["successful_attempts"] = value
        
    
    @property
    def camera_pitch(self):
        global drone_global_commands
        return drone_global_commands[self._my_ip]["camera_pitch"]

    @camera_pitch.setter
    def camera_pitch(self, value): 
        global drone_global_commands
        drone_global_commands[self._my_ip]["camera_pitch"] = value
        
    @property
    def socket_initialized(self):
        return self._socket_initialized;

    @socket_initialized.setter
    def socket_initialized(self, value):
        self._socket_initialized = value;
        if hasattr(self, "_flight_listener"):
            if self._flight_listener != None :
                self._flight_listener.set_initialized_socket(value);
    #endregion Aliases


    #region Web events
    def connect(self):
        self.my_log.info("Connexion au serveur de contrôle réussie")
        my_position = None;
        self.socket_initialized = True
        if self._connected and self._initialized:
            my_position = self._drone.get_state(PositionChanged)
        self._brain_client.emit('identify', {"name":self.my_name, "video_port":self._ws_port, "ip":self._my_ip ,"connected": self._connected, "manual": self._manual_unit, "sim":self._on_test, "position":my_position})
    
    def connect_error(self):
        self.socket_initialized = False
        self.my_log.error("Impossible de se connecter au serveur de contrôle")

    def disconnect(self):
        self.socket_initialized = False
        self.my_log.warning("Connexion au serveur de contrôle perdue")
    #endregion Web events

    #region To Upgrade
    #@deprecated(
    #    version="1.0.0",
    #    reason="Retrait de la logique OpenCV"
    #)
    def __init_opencv_frame_queue(self):
        try :
            self.my_log.info("Ouverture du flux pour {}".format(self._my_ip.split(".")))
            self._ws_port = 7000 + int(self._my_ip.split(".")[2])
  
        except (Exception) as error: 
           self.my_log.error("Status de la connectique : ERREUR, tentative de création de la file d'images")
           self.my_log.error(error)


    #@deprecated(
    #    version="1.0.0",
    #    reason="Intégration FFMPEG"
    #)
    def __init_video_streaming(self):
        try : 
            self._camera_initialized = True
        except (Exception) as ex :
            self.my_log.error("Erreur lors de la liaison avec la caméra {}".format(self._my_ip))
            self._camera_initialized = False
            self.my_log.error(ex)

    #@deprecated(
    #    version="1.0.0",
    #    reason="Ancien model de fonctionnement"
    #)
    def SendCommandOld(self, command):
        if not self._on_test and (not self._connected or not self._initialized) :
            return; 

        name = "";#command.name;
        params = None; #command.params

        # Commandes envoyées directement par le programme Python
        if isinstance(command, DroneCommand):
            name = "{}{}".format(command.command_type.value,command.name.value);
            params = command.params
        # Commandes envoyées par WebSocket
        elif isinstance(command, dict):
            name = str(command["name"])
            params = command["params"] if "params" in command.keys() else None
        else :
            self.my_log.error("Mauvaise informations envoyées, aucune interpretation de la commande")
            return;

        try :
            target = getattr(self, name)
            try :

                self.my_log.info("Commande {} reçue, tentative de traitement".format(name, self._failure_count))
                if params is not None:
                    target(params);
                else :
                    target()
                self._failure_count = 0
            except(Exception) as error: 

                self._failure_count += 1
                self.my_log.warning("Commande {} non reçue, tentative #{}".format(name, self._failure_count))
                self.my_log.warning("Détail de l'erreur")
                self.my_log.warning(error)
                
                # On sanctionne tous les échecs
                if self._failure_count >= self._max_retry :
                    raise CommandAbordException()
                time.sleep(1)

                self.SendCommand(command);
        except (CommandAbordException) :
            self.my_log.error("{} échecs, abandon de la commande {}".format(self._failure_count, name))
            self._failure_count = 0
        except (Exception) as any_error: 
            self.my_log.error("Commande {} non trouvée : {}".format(name, any_error))
        
    #endregion To Upgrade