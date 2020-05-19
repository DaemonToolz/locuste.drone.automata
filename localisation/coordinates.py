# Coordinates Classe des coordonées partagées avec la partie GO
class Coordinates(object):
    def __init__(self, lat=None, long=None, alt=None, orientation=None):
        self.UpdatePosition(lat,long,alt, orientation)
    
    def UpdatePosition(self, lat, long, alt, orientation=None):
        if long is not None:
            self.longitude = long
        if lat  is not None:
            self.latitude = lat
        if alt  is not None:
            self.altitude = alt
        if orientation is not None:
            self.orientation = orientation

class DroneHomeRelay(Coordinates):
    pass

class DroneCoordinates(Coordinates):
    pass

from json import JSONEncoder
import json

class CoordinateEncoder(JSONEncoder):
    def default(self, object):
        if isinstance(object, Coordinates):
            return object.__dict__
        else:
            # call base class implementation which takes care of
            # raising exceptions for unsupported types
            return json.JSONEncoder.default(self, object)

 