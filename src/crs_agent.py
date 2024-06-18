from typing import Any, Callable, Coroutine, Dict, List, Optional, Union
import autogen as autogen
from autogen import ConversableAgent
from autogen.agentchat.agent import Agent
from src.plugins import *
import openai
import json
import time
from src.json_utils import fix_and_parse_json
import streamlit as st



get_field_information_prompt = """
You are an expert in the field of {field} recommendation.
You don't know the user's preferences, You need to get the user's real-time preferences through conversation to complete the recommendation, list what you think are the key factors to ask to quickly make the recommendation that the user desires.

Please follow these rules:
1. List at least 7 factors, at most 10 factors.
2. The more informative the factor, the higher the ranking.
3. Introducing the chosen factors in just one sentence.

Please output the edited script in a JSON format of this kind, and only a parsable JSON object.
{{{{
    "xxx": "xxx description",
    "yyy": "yyy description",
    ...
}}}}
"""

decision_prompt = """
You are an excellent conversation recommender in the field of %s. You can through the action of ask to get the user's preferences, and then through the action of recommend to recommend items that meet the user's preferences.
You need to make a decision which action to take based on the user's preferences. History decisions is the action you have taken before.
user preferences:%s  history decisions:%s

Please think step by step before making a decision:
1. Only when there are few items that meet the user's preferences can you make a personalized recommendation, otherwise you need to ask for more information about user's preferences.
2. If the user's preferences are not clear enough, you need to choose the action of ask for more information about user's preferences.
3. If the user's preferences are clear enough, choose the action of recommend.
4. Take the history decisions into account, learning from the failed recommendations.
5. Don't recommend consecutively, you need to ask for more information about user's preferences after recommending.

Output the edited script in a JSON format of this kind, and only a parsable JSON object.
{
    "action": "ask or recommend",
    "thought": "your thought about this decision",
}
"""

ask_response_prompt = """
You are chatting with a user. You want to get the user's preferences through the conversation in the field of {field}.
You task is to get user preferencces through natural conversation.

The following information may help you better tap into user preferences:{information}
User preferences now known:{user_intent}

Please remember the following rules:
1. One question at a time, choose the most important information you think to ask.
2. Give the user some examples of the information you want to ask for.
3. Don't ask for information that is known to be relevant in the user's preferences.
"""

recommend_response_prompt = """
You are an excellent recommender in the field of {field}. You need to recommend items that meet the user's preferences.
Now user preferences:{user_intent}

Please remember the following rules:
1. Select {k} items that best match user preferences recommended to the user.
2. The more relevant the item, the higher the ranking.
3. Convince the user to accept this recommendation based on user preferences and item information.

Output format:
item1 title : item1 description
item2 title : item2 description
...
itemk title : itemk description
"""

response_v2_prompt = """
You are an excellent conversation recommender in the {field} domin, your task is guide users to  discover their preferences by presenting information about the recommended items.

Please remember the following point:
1.Users are not clear about their preferences, you need to show users different information to guide them to discover their interests.
2.You can only guide users to discover their own interests by recommending items, don't ask users directly for their preferences.
3.Summarising the key information about each recommended item into tags can better guide the user.
4.Tags need to contain important information about the item, such as director, actor, etc. in film, era, style, etc. in music.
5.The number of tags at least 5, at most 10.

Let's think step by step:
1.Summarise known user preferences from the dialogue.
2.Choose {k} items that meet the user's preferences and summarise the key information about each item into tags as the reason for recommendation.
3.Ask the user if they are interested in some of the information mentioned.

Items description as follows format:
item title
Tags: tag1, tag2, tag3,...
Description: tag's description.
"""

user_intent_prompt = """
You're very good at user intent understanding. 
Now you are given a conversation, you need to understand the user's preferences from the conversation, and output the user's preferences.

Please remember the following rules:
1. Summarize the user's preferences in the third person.
2. Summarise the reasons why users reject recommendations.

Below is an example of a conversation and the user's preferences:
conversation:
System: Do you prefer male or female singers?
User: I'm looking for some female singers.
System: What type of singers do you like?
User: I like some country-pop singers, like Taylor Swift.

user preferences:
The user is looking for some female singers in the country pop genre, He likes singers like Tyler.
"""

extra_items_prompt = """
You are an excellent assistant in the field of {field}.
You need to extra the title and description of the item in the field of {field} in the conversation content.

Please output the edited script in a JSON format of this kind, and only a parsable JSON object.
{{{{
    "item1 title": "item1 description",
    "item2 title": "item2 description",
    ...
}}}}
If there is no item in the conversation content, please output an empty JSON object.
"""

sys_msg = """
You are an excellent assistant.
"""

class CRSAgent(ConversableAgent):
    def __init__(self, 
        name: str,
        llm_config: dict,
        max_turn: int,
        field: str = "film",
        k: int = 5,
        human_input_mode = "NEVER",     
    ):
        super().__init__(
            name=name,
            llm_config=llm_config,
            max_consecutive_auto_reply=max_turn,
            system_message=sys_msg,
            human_input_mode=human_input_mode,
        )
        self.field = field
        self.k = k
        self.messages = list()
        self.ask_messages = list()
        self.decision_messages = list()
        self.human_input_mode = human_input_mode
        
        self.field_information = self._get_field_information()
        
        self.register_reply([Agent, None], CRSAgent._generate_user_sim_reply, position=1)
        
    def reset(self):
        self.messages = list()
        self.ask_messages = list()
        self.decision_messages = list()
        
    def response_v1(self, ):
        conv_content = self._get_conversation_content()
        user_intent = self._get_user_intent(conv_content)
        action = self._get_action(user_intent)
        # print(action)
        rec_items = None
        if action['action'] == 'ask':
            response = self._ask_response(user_intent) 
        elif action['action'] == 'recommend':
            response = self._recommend_response(user_intent)
            # rec_items = self._extra_items(response)
            
        return response, action    
        
    def response(self):    
        messages = [
            {"role": "system", "content": response_v2_prompt.format(field=self.field, k=self.k)},
        ]
        messages += self.messages
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k", temperature=0, messages=messages, stream=False,
        )
        response = response["choices"][0]["message"]["content"]
        rec_items = self._extra_items(response)
        if not rec_items:
            rec_items = None
        # self.messages += [{"role": "assistant", "content": response}]
        
        return response, rec_items 

    
    def _generate_user_sim_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[autogen.Agent] = None,
        config: Optional[Any] = None,
    ) -> Union[str, Dict, None]:
        message = messages[-1]
        # print(messages)
        self.messages += [message]
        if (self._consecutive_auto_reply_counter[sender] == 1):
            response = "Hello, how can i help you today?\n"
            self.ask_messages += [{"role": "assistant", "content": response}]
        else:
            conv_content = self._get_conversation_content()
            user_intent = self._get_user_intent(conv_content)
            response, rec_items = self.response_v1(user_intent)
            # response, rec_items = self.response()
            self.messages += [{"role": "assistant", "content": response}]
        # if (self._consecutive_auto_reply_counter[sender] >= 5):
        #     return True, None
        return True, response
    
    def _get_conversation_content(self):
        conv_content = ""
        for message in self.messages:
            if message['role'] == 'assistant':
                conv_content += f"System:{message['content']}\n"
            elif message['role'] == 'user':
                conv_content += f"User:{message['content']}\n"
        
        return conv_content
    
    def _get_field_information(self):
        messages = [
            {"role": "system", "content": get_field_information_prompt.format(field=self.field)},
        ]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", temperature=0, messages=messages, stream=False,
        )
        field_information = response["choices"][0]["message"]["content"]
        
        return field_information
    
    def _get_action(self, user_intent):
        messages = [
            {"role": "system", "content": decision_prompt % (self.field, user_intent, self.decision_messages)},
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", temperature=0, messages=messages, stream=False,
        )
        response = response["choices"][0]["message"]["content"]
        action = fix_and_parse_json(response)
        if not action:
            action = {'action': 'recommend', 'thought': 'I don\'t have enough information about the user\'s preferences to make a personalized recommendation. I need to ask for more information about the user\'s film preferences.'}
        elif action['action'] == 'recommend':
            action['result'] = 'recommend failed'

        self.decision_messages += [{'role': 'assistant', 'content': json.dumps(action)}]
        
        return action
    
    def _ask_response(self, user_intent):
        messages = [
            {"role": "system", "content": ask_response_prompt.format(field=self.field, information=self.field_information, user_intent=user_intent)},
        ]
        messages += self.ask_messages
        # print(self.ask_messages)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", temperature=0.0, messages=messages, stream=False,
        )
        ask_response = response["choices"][0]["message"]["content"]
        # self.messages += [{"role": "assistant", "content": ask_response}]
        self.ask_messages += [{"role": "assistant", "content": ask_response}]
        
        return ask_response

    def _recommend_response(self, user_intent):
        messages = [
            {"role": "system", "content": recommend_response_prompt.format(field=self.field, user_intent=user_intent, k=self.k)},
        ]
        messages += self.messages
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k", temperature=0, messages=messages, stream=False,
        )
        rec_response = response["choices"][0]["message"]["content"]
        # self.messages += [{"role": "assistant", "content": rec_response}]
        # items = fix_and_parse_json(rec_response)
        
        return rec_response

    def _get_user_intent(self, conv_content):
        messages = [
            {"role": "system", "content": user_intent_prompt},
        ]
        messages += [{"role": "user", "content": conv_content}]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", temperature=0, messages=messages, stream=False,
        )
        user_intent = response["choices"][0]["message"]["content"]
        
        return user_intent
    
    def _extra_items(self, content):
        messages = [
            {"role": "system", "content": extra_items_prompt.format(field=self.field)},
        ]
        messages += [{"role": "user", "content": content}]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k", temperature=0, messages=messages, stream=False,
        )
        response = response["choices"][0]["message"]["content"]
        items = fix_and_parse_json(response)
        if not items:
            items = {}
        # print(items)
        return items
    
