from src.config import set_key
from src.utils import my_stop_after_attempt, my_wait_exponential
from tenacity import Retrying, retry_if_not_exception_type
import openai


set_key()

planner_prompt = """
You are chatting with a user, now you need choose an action based on the user preferences.

You can choose from the following actions:
- Ask: If the user's preferences are not clear, you could ask the user for more information to better understand their preferences.
- Recommend: If the user's preferences are clear, you can give the user a personalized recommendation based on the user's preferences.

Output the action you choose and output the thought for your choice as a reason.

User preferences: The user prefers comedy movies.
Output: Ask # There are many comedy movies, I need to ask the user for more information to better understand their preferences, such as director, actor, etc.

User preferences: The user is a fan of Steven Spielberg, and likes comedy movies.
Output: Recommend # I can give the user a personalized recommendation based on the user's preferences about the director and genre.

User preferences: {preferences}
"""

summarize_prompt = """
Given an conversation, summarize the user's preferences about movies.

Conversation:
- User: I am looking for some action movies.
- Recommender: Which director do you prefer?
- User: I prefer the director Steven Spielberg.
- Recommender: Which actor do you prefer?
- User: All ok.
Output:
The user prefers action movies directed by Steven Spielberg and does not have a specific preference for actors.

Conversation: {conversation}
"""

ask_prompt = """
You are chatting with a user. You want to get the user's preferences through the conversation in the field of movie.
You task is to get user preferencces through natural conversation.

The following information may help you better tap into user preferences:[genre, director, actor, release_date, runtime, language]

Please remember the following rules:
1. One question at a time, choose the most important information you think to ask.
2. Give the user some examples of the information you want to ask for.
3. Don't ask for information that is known to be relevant in the user's preferences.
"""

recommend_prompt = """
You are an excellent movie recommender. Your goal is to provide a personalized recommendation based on the user's preferences.

Now the user's preferences are: {preferences}

Please remember the following rules:
- Select the most relevant {k} movies according to the user's preferences.
- The higher the relevance, the higher the ranking in the recommendation list.

Output only a list of recommended movies, for example: [movie1 title, movie2 title, movie3 title, ..., movie{k} title]"
"""

class CRSAgent():
    def __init__(self, k=10):
        self.k = k
        
        self.oai_messages = list()
        self.last_action = None
        self.last_preferences = None
        self.action_count = 0
        self.action_list = ['Ask', 'Recommend']
    
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
                    max_tokens=2048,
                    request_timeout=50
                )
            request_timeout = min(300, request_timeout * 2)
        return response.choices[0].message["content"]
    
    def reset(self):
        self.oai_messages = list()
        self.last_action = None
        self.last_preferences = None
        self.action_count = 0
        
    def step(self, user_input):
        self.oai_messages.append({"role":"user", "content" : user_input})
        user_preferences = self._summrize_user_preferences()
        
        # Rule1: 手动处理action history，不要连续3次以上的同样的action
        action = None
        if self.last_action is not None and self.action_count >= 3:
            if self.last_action == 'Ask':
                action = 'Recommend'
            elif self.last_action == 'Recommend':
                action = 'Ask'
        else:
            # Rule3: 这里其实如果prompt表现不好，可以设置为ask，即刚进入对话时，询问用户的偏好
            if self.last_action == None:
                action = 'Ask'
            else:
                action = self._get_action(user_preferences)
                # print(action)
                action = action.split("#")[0].strip()
        
        if 'Ask' in action:
            response = self._ask_action()
        elif 'Recommend' in action:
            response = self._recommend_action(user_preferences)
        else:
            response = self._ask_action()
            # raise ValueError(f"Unknown action: {action}")
        
        if action == self.last_action:
            self.action_count += 1
        else:    
            self.last_action = action
            self.action_count = 1
        self.oai_messages.append({"role":"assistant", "content" : response})
        # print(self.oai_messages)
        
        return response, action
            
    def _get_action(self, preferences):
        messages = [{"role":"system", "content" : planner_prompt.format(preferences=preferences)}]
        return self.call_openai_response(messages)
    
    def _summrize_user_preferences(self):
        conversation = self._prepare_conversation()
        messages = [{"role":"system", "content" : summarize_prompt.format(conversation=conversation)}]
        return self.call_openai_response(messages)
    
    def _ask_action(self):
        messages = [{"role":"system", "content" : ask_prompt}]
        messages.extend(self.oai_messages)
        return self.call_openai_response(messages)
    
    def _recommend_action(self, user_preferences):
        messages = [{"role":"system", "content" : recommend_prompt.format(preferences=user_preferences, k=self.k)}]
        return self.call_openai_response(messages)
    
    def _prepare_conversation(self):
        conversation = ""
        for message in self.oai_messages:
            if message['role'] == 'user':
                conversation += f"- User: {message['content']}\n"
            elif message['role'] == 'assistant':
                conversation += f"- Recommender: {message['content']}\n"
            else:
                raise ValueError(f"Unknown role: {message['role']}")
            
        return conversation
