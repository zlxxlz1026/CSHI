from src.plugins import *
import os


class Plugin():
    def __init__(self):
        self.handlers = {}
    
    def load_config(self) -> dict:
        plugin_conf = PluginManager().get_plugin_config(self.name)
        return plugin_conf


    