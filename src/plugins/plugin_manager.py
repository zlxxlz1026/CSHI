from .singleton import singleton
from .sorted_list import SortedList
from .message import Message
import os
import json
import importlib


@singleton
class PluginManager():
    def __init__(self):
        self.plugins = dict()
        self.plugins_instance = dict()
        self.plugins_config = dict()
        self.stages_config = dict()
        self.loaded_plugins = dict()
        self.listening_plugins = dict() 
         
    def register(self, name: str, enabled: bool, **kwargs):
        def warpper(cls):
            cls.name = name
            cls.enabled = enabled
            self.plugins[name.lower()] = cls           
        return warpper
    
    def start(self):
        #1.load stage config and plugin config
        self._load_plugins_config()
        self._load_stages_config()
        #2.load plugins
        self._load_plugins()
        #3.generate plugins instance
        self._activate_plugins()
        #4.after all plugins loaded, check all plugins handlers
        self._check_all_plugins_handlers()
        #5.sort plugins by priority each stage
        self._sort_plugins()
        
    def execute_stage(self, stage: str, message: Message, *args, **kwargs) -> Message:
        sorted_plugins_list = self.listening_plugins[stage].get_sorted_list()
        # print(f"stage: {stage}, sorted_plugins_list: {sorted_plugins_list}")
        for plugin_name in sorted_plugins_list:
            plugin_instance = self.plugins_instance.get(plugin_name)
            plugin_instance.handlers[stage](message, *args, **kwargs)
            #TODO: 目前的逻辑先不考虑直接退出，后续可以考虑加入退出逻辑
        return message

    
    def _load_plugins_config(self):
        '''
        加载所有插件的参数配置
        '''
        config_path = os.path.join(os.getcwd(), "../src/plugins/plugins_config.json")
        # print(config_path)
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding='utf-8') as f:
                    all_config = json.load(f)
                    print(f"load all config from: {config_path}")
                    for k in all_config:
                        self.plugins_config[k.lower()] = all_config[k]
        except Exception as e:
            print(f"load all config failed: {e}")
    
    def _load_stages_config(self):
        stages_path = os.path.join(os.getcwd(), "../src/plugins/stages_config.json")
        try:
            if os.path.exists(stages_path):
                with open(stages_path, "r", encoding='utf-8') as f:
                    all_config = json.load(f)
                    print(f"load all stage config from: {stages_path}")
                    for k in all_config:
                        self.stages_config[k.lower()] = all_config[k]
        except Exception as e:
            print(f"load all stage config failed: {e}")
    
    def _sort_plugins(self):
        for stage in self.stages_config.keys():
            self.listening_plugins[stage] = SortedList(reverse=False)
        for stage in self.stages_config.keys():
            self.listening_plugins[stage].clear()
            for plugin_name in self.stages_config[stage]:
                if plugin_name.lower() not in self.plugins:
                    raise Exception(f"Plugin {plugin_name} not found")
                elif plugin_name.lower() not in self.plugins_instance:
                    continue
                else:
                    self.listening_plugins[stage].append((self.stages_config[stage][plugin_name.lower()]['priority'], plugin_name.lower()))
        # print(self.listening_plugins)

    def _check_plugin_handlers(self, plugin_name: str) -> bool:
        instance = self.plugins_instance.get(plugin_name.lower())
        for stage in self.stages_config.keys():
            if plugin_name.lower() in self.stages_config[stage] and instance.handlers.get(stage) is None:
                return False
        return True
    
    def _check_all_plugins_handlers(self) -> bool:
        for plugin_name in self.plugins_instance.keys():
            if not self._check_plugin_handlers(plugin_name):
                raise Exception(f"Plugin {plugin_name} has no handlers for all stages")
        return True
    
    def _load_plugins(self):
        """
        Load plugins from the specified plugins directory.

        This method iterates over the files in the plugins directory and loads each plugin
        that is a valid Python package. The loaded plugins are stored in the `loaded_plugins`
        dictionary attribute of the plugin manager.

        Returns:
            None
        """
        plugins_path = "../Agent4CRS/plugins/"
        for plugin_name in os.listdir(plugins_path):
            # print(plugin_name)
            plugin_path = os.path.join(plugins_path, plugin_name)
            if os.path.isdir(plugin_path):
                module_path = os.path.join(plugin_path, "__init__.py")
                if os.path.isfile(module_path):
                    # print(self.plugins)
                    self.loaded_plugins[plugin_name] = importlib.import_module(f"Agent4CRS.plugins.{plugin_name}")
    
    def _activate_plugins(self):
        for name, plugincls in self.plugins.items():
            if plugincls.enabled:
                try:
                    instance = plugincls()
                    print(f"Plugin {name} activated")
                #TODO: 这里可以捕获异常报告不影响其他插件的执行，但是目前直接抛出异常
                except:
                    raise Exception(f"Failed to instantiate plugin {name}")
                self.plugins_instance[name] = instance            
    
    def get_plugin_config(self, plugin_name: str) -> dict:
        plugin_conf = self.plugins_config.get(plugin_name.lower())
        if not plugin_conf:
            return {}
        return plugin_conf
