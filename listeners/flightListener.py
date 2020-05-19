import sys
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, '../log')

#region OLYMPE
import olympe
from olympe.messages.common.CommonState import BatteryStateChanged
from olympe.messages.wifi import rssi_changed
from olympe.messages.ardrone3.GPSState import NumberOfSatelliteChanged
from olympe.messages.ardrone3.PilotingState import (
    PositionChanged,
    AlertStateChanged,
    FlyingStateChanged,
    NavigateHomeStateChanged,
    moveToChanged
)
from olympe.messages.ardrone3.GPSSettingsState import HomeChanged, GPSFixStateChanged
#endregion OLYMPE
import log.log

# FlightListener Regroupe tous les états intéressants envoyés par le drone PARROT / AR.SDK
# Voir https://github.com/Parrot-Developers/olympe
class FlightListener(olympe.EventListener):
    def set_logger(self, logger):
        self.my_log = logger;
    
    def set_socket(self, websocket):
        self._brain_client = websocket;

    def set_relay(self, relay):
        self._relay = relay

    def set_drone_coordinates(self, coordinates):
        self._drone_coordinates = coordinates

    def set_initialized_socket(self, initialized):
        self._socket_initialized = initialized;

    def set_my_name(self, name):
        self.my_name = name;

    @olympe.listen_event(FlyingStateChanged() | AlertStateChanged() | NavigateHomeStateChanged())
    def onStateChanged(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info("{} = {}".format(event.message.name, event.args["state"]))

        if hasattr(self, "_socket_initialized") and hasattr(self, "my_name") and hasattr(self,"_brain_client"):
            if self._socket_initialized:
                try :
                    self._brain_client.emit('internal_status_changed', {"id":self.my_name,"status": event.message.name, "result":event.args["state"]})
                except(Exception) as error :
                    if hasattr(self, "my_log"):
                        self.my_log.error("Une erreur est survenue")
                        self.my_log.error(error)
                        self.my_log.error("{} = {}".format(event.message.name, event.args["state"]))
                        
    @olympe.listen_event(PositionChanged())
    def onPositionChanged(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info(
                "latitude = {} longitude = {} altitude = {}".format(
                  event.args["latitude"],
                  event.args["longitude"],
                  event.args["altitude"]
               )
            )
        if hasattr(self, "_drone_coordinates"):
            self._drone_coordinates.UpdatePosition(event.args["latitude"], event.args["longitude"], event.args["altitude"])
        
            if hasattr(self, "_socket_initialized") and hasattr(self, "my_name") and hasattr(self,"_brain_client"):
                if self._socket_initialized:
                    self._brain_client.emit('position_update', {"id":self.my_name,"latitude": event.args["latitude"], "longitude": event.args["longitude"], "altitude": event.args["altitude"] })  

    @olympe.listen_event(GPSFixStateChanged() )
    def onGPSChanged(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info(event);
        if hasattr(self, "_socket_initialized") and hasattr(self, "my_name") and hasattr(self,"_brain_client"):
            if self._socket_initialized:
                self._brain_client.emit('internal_status_changed', {"id":self.my_name, "status":event.message.name, "result":event.args["fixed"]})



    @olympe.listen_event(HomeChanged() )
    def onHomeChanged(self, event, scheduler):
        if hasattr(self, "my_log"):
              self.my_log.info(
                "latitude = {} longitude = {} altitude = {}".format(
                  event.args["latitude"],
                  event.args["longitude"],
                  event.args["altitude"]
               )
            )
        if hasattr(self, "_relay"):
            self._relay.UpdatePosition(event.args["latitude"], event.args["longitude"], event.args["altitude"])
            if hasattr(self, "_socket_initialized") and hasattr(self, "my_name") and hasattr(self,"_brain_client"):
                if self._socket_initialized:
                    self._brain_client.emit('home_position_update', {"id":self.my_name,"latitude": event.args["latitude"], "longitude": event.args["longitude"], "altitude": event.args["altitude"] })       


    @olympe.listen_event(moveToChanged())
    def onMovedTo(self, event, scheduler):
        if hasattr(self, "my_log"):
               self.my_log.info(
                "latitude = {} longitude = {} altitude = {}".format(
                  event.args["latitude"],
                  event.args["longitude"],
                  event.args["altitude"]
               )
            )
        if hasattr(self, "_drone_coordinates"):
            self._drone_coordinates.UpdatePosition(event.args["latitude"], event.args["longitude"], event.args["altitude"])
            if hasattr(self, "_socket_initialized") and hasattr(self, "my_name") and hasattr(self,"_brain_client"):
                if self._socket_initialized:
                    self._brain_client.emit('position_update', {"id":self.my_name,"latitude": event.args["latitude"], "longitude": event.args["longitude"], "altitude": event.args["altitude"] })       


    @olympe.listen_event(NumberOfSatelliteChanged())
    def onSatelliteChanged(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info(event);
        if hasattr(self, "_socket_initialized") and hasattr(self, "my_name") and hasattr(self,"_brain_client"):
            if self._socket_initialized:
                self._brain_client.emit('internal_status_changed', {"id":self.my_name, "status":event.message.name, "result":event.args["numberOfSatellite"]})


    @olympe.listen_event(BatteryStateChanged())
    def onBatteryUpdate(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info(event);
        if hasattr(self, "_socket_initialized") and hasattr(self, "my_name") and hasattr(self,"_brain_client"):
            if self._socket_initialized:
                self._brain_client.emit('internal_status_changed', {"id":self.my_name, "status":event.message.name, "result":event.args["percent"]})


    @olympe.listen_event(
        FlyingStateChanged(state="motor_ramping")
        >> FlyingStateChanged(state="takingoff", _timeout=1.)
        >> FlyingStateChanged(state="hovering", _timeout=5.)
    )
    def onTakeOff(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info("Décollage du drone")
        if hasattr(self, "_socket_initialized") and hasattr(self, "my_name") and hasattr(self,"_brain_client"):
            if self._socket_initialized:
                self._brain_client.emit('internal_status_changed', {"id":self.my_name, "status":event.message.name, "result":"success"})

    @olympe.listen_event(rssi_changed())
    def onSignalChanged(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info(event.args)
        
        if hasattr(self, "_socket_initialized") and hasattr(self, "my_name") and hasattr(self,"_brain_client"):
            if self._socket_initialized:
                self._brain_client.emit('internal_status_changed', {"id":self.my_name, "status":event.message.name, "result":event.args["rssi"]})
        
