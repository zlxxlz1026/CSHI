from src.plugins import *
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union
import os
from src.config import set_key
import json


set_key()


class UserSimNLP():
    def __init__(
        self,
        name="redial",
        max_turn=10,
        ):
        self.name = name
        self.max_turn = max_turn
        PluginManager().start()
        self.message = Message(content=None, message_type=None)
        self.message['dataset'] = self.name
        if not os.path.exists(f"../Agent4CRS/user_profile/{self.name}/"):
            os.makedirs(f"../Agent4CRS/user_profile/{self.name}")
        
    def reset(self, user_id, target_item):
        # print(PluginManager().stages_config)
        self.message['user_id'] = user_id
        # 针对某些数据集不需要长期偏好初始化阶段
        if not os.path.exists(f"../Agent4CRS/user_profile/{self.name}/{user_id}.json"):
            with open(f"../Agent4CRS/user_profile/{self.name}/{user_id}.json", "w") as f:
                json.dump({}, f)
            
        self.message['content'] = target_item
        self.message['message_type'] = str
        self.message['target_items'] = [target_item]
        self.message['oai_messages'] = list()
        self.message['turn'] = 0
        PluginManager().execute_stage("real_time_preference_init", self.message)

    def get_intent(self):
        return self.message['intent']
    
    def generate_reply(self,
                       messages: Optional[List[Dict]] = None,):
        '''
        messages: conversation history
        '''
        self.message['content'] = messages[-1]['content']
        self.message["oai_messages"] = messages
        PluginManager().execute_stage("handle_message", self.message)
        self.message["oai_messages"].append({"role": "assistant", "content": self.message['reply']})
        self.message['turn'] += 1
        return True, self.message['reply']
