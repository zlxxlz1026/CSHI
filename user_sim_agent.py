from src.plugins import *
import os 
import pandas as pd
import json
from token_count_utils import count_token


sys_prompt1 = """You are a seeker chatting with a recommender for recommendation. Your target items: {target_item}. You must follow the instructions below during chat.
If the recommender recommend {target_item}, you should accept.
If the recommender recommend other items, you should refuse them and provide the information about {target_item}. You should never directly tell the target item title.
If the recommender asks for your preference, you should provide the information about {target_item}. You should never directly tell the target item title.
"""

sys_prompt2 = """You are a seeker chatting with a recommender for recommendation. Your target items: {target_item}. You must follow the instructions below during chat.
Here is the information about target item: {item_info}. Your history is: {history}.
You could provide your history.
If the recommender recommend {target_item}, you should accept.
If the recommender recommend other items, you should refuse them and provide the information about {target_item}.
If the recommender asks for your preference, you should provide the information about {target_item}.
You should never directly tell the target item title.
"""

item_info_prompt = """
You are an movie expert, you are going to generate a movie basic information when given a movie title.

The movie title is: {target_item}
My request is "I need help generating the given movie basic information, including genres, director, runtime, release date, actors, etc."

Strictly follow the output format below:
title: <the movie title>
genres: <the movie genres>
...
"""

class UserSimV1:
    def __init__(self):
        self.target_item = None
        self.oai_messages = []
    
    def reset(self, target_item):
        self.target_item = target_item
        self.oai_messages = []
    
    def step(self, response):
        self.oai_messages.append({"role": "user", "content": response})
        response = self.get_response()
        self.oai_messages.append({"role": "assistant", "content": response})
        return response
    
    def call_openai_response(self, messages):
        request_timeout = 20
        for attempt in Retrying(
            reraise=True,
            retry=retry_if_not_exception_type((openai.error.InvalidRequestError)),
            wait=my_wait_exponential(min=1, max=60), stop=(my_stop_after_attempt(8))
        ):
            with attempt:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo-0125",
                    messages=messages,
                    temperature=0,
                    max_tokens=4096,
                    request_timeout=50
                )
            request_timeout = min(300, request_timeout * 2)
        return response.choices[0].message["content"]
    
    def get_response(self):
        messages = [{"role": "system", "content": sys_prompt1.format(target_item=self.target_item)}]
        messages.extend(self.oai_messages)
        return self.call_openai_response(messages)

    
class UserSimV2:
    def __init__(self):
        self.target_item = None
        self.oai_messages = list()
        self.user_id = None
        
        with open('./exp1_user_profile.jsonl', 'r', encoding='utf-8') as f:
            self.user_profiles = json.load(f)
    
    def call_openai_response(self, messages):
        request_timeout = 20
        for attempt in Retrying(
            reraise=True,
            retry=retry_if_not_exception_type((openai.error.InvalidRequestError)),
            wait=my_wait_exponential(min=1, max=60), stop=(my_stop_after_attempt(8))
        ):
            with attempt:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo-0125",
                    messages=messages,
                    temperature=0,
                    max_tokens=4096,
                    request_timeout=50
                )
            request_timeout = min(300, request_timeout * 2)
        return response.choices[0].message["content"]
    
    def reset(self, target_item, user_id):
        self.target_item = target_item
        self.oai_messages = list()
        self.user_id = user_id
        self.history = {"like_movies": self.user_profiles[str(user_id)]["like_movies"][-5:], "dislike_movies": self.user_profiles[str(user_id)]["dislike_movies"][-5:]}
        self.item_info = self.get_item_info()
    
    def step(self, response):
        self.oai_messages.append({"role": "user", "content": response})
        response = self.get_response()
        self.oai_messages.append({"role": "assistant", "content": response})
        return response
    
    def get_response(self):
        messages = [{"role": "system", "content": sys_prompt2.format(target_item=self.target_item, item_info=self.item_info, history=self.history)}]
        # print(messages)
        messages.extend(self.oai_messages)
        return self.call_openai_response(messages)
    
    def get_item_info(self):
        messages = [{"role": "system", "content": item_info_prompt.format(target_item=self.target_item)}]
        response = self.call_openai_response(messages)
        t_list = response.split("\n")
        res = dict()
        for t in t_list:
            if ":" not in t:
                continue
            t = t.split(":")
            res[t[0]] = t[1].strip()
        tag_list = list(res.keys())
        if "actors" in tag_list:
            res["actors"] = res["actors"].split(",")[0]
        if "director" in tag_list:
            res["director"] = res["director"].split(",")[0]
        
        return res
    
class UserSimV3:
    def __init__(self, dataset_name='movielens'):
        self.user_id = None
        self.target_item = None
        self.oai_messages = list()
        self.message = Message(content=None, message_type=None)
        self.message['dataset'] = dataset_name
        PluginManager().start()
    
    def reset(self, target_item: str, user_id: int):
        self.message['user_id'] = user_id
        self.message['target_items'] = [target_item]
        self.message['oai_messages'] = list()
        self.message['turn'] = 0
        self.message['content'] = target_item
        self.message['message_type'] = str
        PluginManager().execute_stage("user_profile_init", self.message)
        PluginManager().execute_stage("real_time_preference_init", self.message)
    
    def step(self, response):
        self.oai_messages.append({"role": "user", "content": response})
        while count_token(self.oai_messages) > 10000:
            self.oai_messages = self.oai_messages[1:]
        self.message['content'] = response
        self.message['oai_messages'] = self.oai_messages
        PluginManager().execute_stage("handle_message", self.message)
        self.oai_messages.append({"role": "assistant", "content": self.message['reply']})
        self.message['turn'] += 1
        return self.message['reply']