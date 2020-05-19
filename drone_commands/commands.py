from enum import Enum

# CommandType Type de commande à envoyer
class CommandType(Enum):
    AUTOMATIC = "Automatic"
    MANUAL = "Manual"
    COMMON = "Common"


# PublicCommands Toutes les commandes publiques 
class PublicCommands(Enum):
    GOTO = "GoTo"
    STOP = "CancelGoTo"
    CAM_DOWN = "SetCameraDown"
    CAM_STD = "SetStandardCamera"
    TAKE_OFF = "TakeOff"
    GO_HOME = "GoHome"
    MOVE = "Move"
    CAM_ORIENTATION = "TiltCamera"


# DroneActionType Listing des états possibles pour le drone
class DroneActionStatus(Enum):
    IDLE = 0
    ON_ACTION = 1

def enumFromValue (enum, name):
    value = enum[name].value
    return value


# DroneCommandParams Objet passé en paramètre par le service locust.service.brain
class DroneCommandParams(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def ToString(self):
        return str(self.__dict__)

# DroneCommand Commande passée à l'automate
class DroneCommand(object):
    def __init__(self, name, params=None, command_type = CommandType.AUTOMATIC):
        self.name = name
        self.params = params
        self.command_type = command_type
    def ToString(self):
        return str(self.__dict__)

class CommandAbordException(Exception):
    pass

