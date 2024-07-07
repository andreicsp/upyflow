from collections import namedtuple


class Controller:
    def __init__(self, config):
        self.config = config


class HttpController(Controller):
    pass

class BluetoothController(Controller):
    pass

class InactiveController(Controller):
    pass


class App(Controller):
    def __init__(self, config, controllers):
        super().__init__(config)
        self.controllers = controllers

    @classmethod
    def create(cls, config, controllers):
        return cls(config, controllers)


AppConfig = namedtuple('AppConfig', ['active_controllers', 'device_id'])

def load_config(config_class):
    return config_class(active_controllers=['http', 'bluetooth'], device_id='1234')
