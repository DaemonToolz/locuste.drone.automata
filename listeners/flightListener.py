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

    def on_signal_lost (self, func):
        self._on_signal_lost = func;


    @olympe.listen_event(FlyingStateChanged() | AlertStateChanged() | NavigateHomeStateChanged())
    def on_state_changed(self, event, scheduler):
        try :
            if hasattr(self, "my_log"):
                self.my_log.info("{} = {}".format(event.message.name, event.args["state"]))
            self.on_internal_status_changed(event.message.name, event.args["state"])
        except :
            pass;      

    @olympe.listen_event(PositionChanged() | moveToChanged())
    def on_position_changed(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info(
                "latitude = {} longitude = {} altitude = {}".format(
                  event.args["latitude"],
                  event.args["longitude"],
                  event.args["altitude"]
               )
            )
        if hasattr(self, "_drone_coordinates"):
            self._drone_coordinates.update_position(event.args["latitude"], event.args["longitude"], event.args["altitude"])
            self.on_element_position_update('position_update', event)

    @olympe.listen_event(HomeChanged())
    def on_home_changed(self, event, scheduler):
        if hasattr(self, "my_log"):
              self.my_log.info(
                "latitude = {} longitude = {} altitude = {}".format(
                  event.args["latitude"],
                  event.args["longitude"],
                  event.args["altitude"]
               )
            )
        if hasattr(self, "_relay"):
            self._relay.update_position(event.args["latitude"], event.args["longitude"], event.args["altitude"])
            self.on_element_position_update('home_position_update', event)

    @olympe.listen_event(
        FlyingStateChanged(state="motor_ramping")
        >> FlyingStateChanged(state="takingoff", _timeout=1.)
        >> FlyingStateChanged(state="hovering", _timeout=5.)
    )
    def on_take_off(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info("Décollage du drone")
        self.on_internal_status_changed(event.message.name, event.args["success"])

    @olympe.listen_event(rssi_changed())
    def on_signal_changed(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info(event.args)
        self.on_internal_status_changed(event.message.name, event.args["rssi"])
        if hasattr(self, "_on_signal_lost") and event.args["rssi"] <= -120:
            self._on_signal_lost()

    @olympe.listen_event(NumberOfSatelliteChanged())
    def on_satellite_changed(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info(event);
        self.on_internal_status_changed(event.message.name, event.args["numberOfSatellite"])

    @olympe.listen_event(BatteryStateChanged())
    def on_battery_update(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info(event);
        self.on_internal_status_changed(event.message.name, event.args["percent"])
  
    @olympe.listen_event(GPSFixStateChanged())
    def on_gps_changed(self, event, scheduler):
        if hasattr(self, "my_log"):
            self.my_log.info(event);
        self.on_internal_status_changed(event.message.name, event.args["fixed"])
  
    def on_internal_status_changed(self, name, value):
        try :
            if hasattr(self, "_socket_initialized") and hasattr(self, "my_name") and hasattr(self,"_brain_client") and self._socket_initialized:
                self._brain_client.emit('internal_status_changed', {"id":self.my_name, "status":name, "result":value})
        except(Exception) as error :
            if hasattr(self, "my_log"):
                self.my_log.error("Une erreur est survenue lors de la mise à jour des états interne")
                self.my_log.error(error)
                self.my_log.error("{} = {}".format(value.message.name, value.args))
                        
    def on_element_position_update(self, event, value): 
        try :
            if hasattr(self, "_socket_initialized") and hasattr(self, "my_name") and hasattr(self,"_brain_client") and self._socket_initialized:
                self._brain_client.emit(event, {"id":self.my_name,"latitude": value.args["latitude"], "longitude": value.args["longitude"], "altitude": value.args["altitude"] })
        except(Exception) as error :
            if hasattr(self, "my_log"):
                self.my_log.error("Une erreur est survenue lors de la mise à jour des positions")
                self.my_log.error(error)
                self.my_log.error("{} = {}".format(value.message.name, value.args))