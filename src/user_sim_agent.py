from typing import Any, Callable, Coroutine, Dict, List, Optional, Union
import autogen
from autogen import ConversableAgent
from autogen.agentchat.agent import Agent
from plugins import *
import pandas as pd


class UserSimAgent(ConversableAgent):
    def __init__(self, 
        name: str,
        llm_config: dict,
        max_turn: int,
        human_input_mode="NEVER",
        ):
        super().__init__(name, llm_config=llm_config, max_consecutive_auto_reply=max_turn, human_input_mode=human_input_mode)
        PluginManager().start()
        # raw_ratings = pd.read_csv('./data//ratings.dat', sep='::', engine='python', header=None, names=['user_id', 'movies_id', 'ratings', 'time'])
        # movies_info = pd.read_csv('./data//movies.dat', sep='::', engine='python', header=None, names=['movies_id', 'title', 'genres'], encoding='ISO-8859-1')
        # users_info = pd.read_csv('./data/users.dat', sep='::', engine='python', header=None, names=['user_id', 'gender', 'age', 'occupation', 'zip_code'])
        # message = Message(content=1, message_type=int, ratings=raw_ratings, movies_info=movies_info, users_info=users_info)
        # PluginManager().execute_stage("user_profile_init", message)
        self.register_reply([Agent, None], UserSimAgent._generate_user_sim_reply, position=1)
        
        self.message = Message(content=None, message_type=None)
        
    def reset(self, user_id: int, target_item: str):
        '''
        根据target_item生成实时偏好
        '''
        self.message['user_id'] = user_id
        self.message['content'] = target_item
        self.message['message_type'] = str
        self.message['target_items'] = [target_item]
        self.message['oai_messages'] = list()
        self.message['turn'] = 0
        # print(f"user_id:{self.message['user_id']}, target_item:{self.message['content']}")
        PluginManager().execute_stage("real_time_preference_init", self.message)
        st_write('real_time_preference', self.message['real_time_preference'])
        st_write('known_preference', self.message['known_tag_dict'])
        st_write('unknown_preference', self.message['unknown_tag_dict'])
        st_write('target_item_info', self.message['info_dict'])
    
    def _generate_user_sim_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[autogen.Agent] = None,
        config: Optional[Any] = None,
    ) -> Union[str, Dict, None]:
        #1. 根据交互信息构建Message类
        self.message['content'] = messages[-1]['content']
        self.message["oai_messages"].append({"role": "user", "content": self.message["content"]})
        # print(f"user_id:{self.message['user_id']}")
        PluginManager().execute_stage("handle_message", self.message)
        self.message["oai_messages"].append({"role": "assistant", "content": self.message['reply']})
        if self.message['intent'] == 'recommend' and self.message['result'] == 'acc':
            sender.stop_reply_at_receive(self)
        self.message['turn'] += 1
        
        st_write('real_time_preference', self.message['real_time_preference'])
        return True, self.message["reply"]
        