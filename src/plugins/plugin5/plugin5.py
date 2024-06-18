from src.plugins import *
import json


sys_prompt = """
You are an excellent assistant. Your task is to select the movies that meet the criteria from the given list of films.

Given movie list: {movie_list}. Given conditions: {conditions}.

You must follow the following rules:
1.Selected movies must be included in the given movie list.
2.The number of movies that selected should be less than 5.

If there is no movie that meets the conditions, output NONE.

Otherwise, Strictly follow the output format below:
{{{{
    "movie1": "why it meets the conditions",
    "movie2": "why it meets the conditions",
    ...
}}}}
"""

judge_prompt = """
You are an excellent assistant.

Now given a question: {question}, select the element that is related to the question from the element list: {element_list}.

If there is no related element, choose "NONE".

Strictly follow the output format below:
OUTPUT: [element1, element2, ...]
"""

condition_generate_prompt = """
You are an excellent assistant.

Now Given a condition, generate a description of the condition.

Input: "director: Stephen Chow"
Output: "I am looking for some movies directed by Stephen Chow."

Input: "genres: comedy"
Output: "I am looking for some comedy movies."

Iuput: {condition}
"""

generate_reply_prompt = """
You are an excellent assiatant, you will act as a user who is looking for some movies to watch. Please roleplay the user using the first person pronoun "I".

You task is to generate a smooth and natural reply based on your preference and previous movies you have watched.

Now your preference is: "director: Stephen Chow". Previous movies you have watched related to your preference are: ['kung fu hustle', 'shaolin soccer']

Output:I am a big fan of Stephen Chow. I have watched kung fu hustle and shaolin soccer directed by him, and I really like them.

Now your preference is: {preference}. Previous movies you have watched related to your preference are: {movie_list}

Output:
"""

@register(
    name="plugin5",
    enabled=True,
)
class Plugin5(Plugin):
    def __init__(self):
        super().__init__()
        self.conf = super().load_config()
        self.handlers["handle_message"] = self.handle_message
    
    def _generate_condition(self, condition):
        messages = [{"role":"system", "content": condition_generate_prompt.format(condition=condition)}]
        # print(messages)
        request_timeout = 20
        for attempt in Retrying(
                reraise=True,
                retry=retry_if_not_exception_type((openai.error.InvalidRequestError)),
                wait=my_wait_exponential(min=1, max=60), stop=(my_stop_after_attempt(8))
        ):
            with attempt:
                response = openai.ChatCompletion.create(
                                model=self.conf["model_name"],
                                messages=messages,
                                temperature=0,
                                request_timeout=50
                            )
            request_timeout = min(300, request_timeout * 2)
        return response.choices[0].message["content"].split(':')[-1].strip()
    
    def _generate_reply(self, preference, movie_list):
        messages = [{"role":"system", "content": generate_reply_prompt.format(preference=preference, movie_list=movie_list)}]
        request_timeout = 20
        for attempt in Retrying(
                reraise=True,
                retry=retry_if_not_exception_type((openai.error.InvalidRequestError)),
                wait=my_wait_exponential(min=1, max=60), stop=(my_stop_after_attempt(8))
        ):
            with attempt:
                response = openai.ChatCompletion.create(
                    model=self.conf["model_name"],
                    messages=messages,
                    temperature=0,
                    request_timeout=50
                )
            request_timeout = min(300, request_timeout * 2)
        reply = response.choices[0].message["content"].replace("OUTPUT:", "").strip()
        return reply
    
    def handle_message(self, message: Message) -> None:
        if message.get("intent") != "ask":
            return
        message['to_plugin4'] = True
        realted_attr_list = message.get("realted_attr_list")
        known_tag_list = message.get("known_tag_list")
        trigger = self.conf["trigger"]
        dataset_name = message.get("dataset")
        print(f"realted_attr_list: {realted_attr_list}\nknown_tag_list: {known_tag_list}\ntrigger: {trigger}\nunknown_tag_list: {message.get('unknown_tag_list')}")

        if len(set(realted_attr_list) & set(known_tag_list) & set(trigger)) == 0 or realted_attr_list[0] == 'NONE':
            return

        user_id = message.get("user_id")
        with open("../Agent4CRS/user_profile/{dataset_name}/{user_id}.json".format(user_id=user_id, dataset_name=dataset_name), "r") as f:
            user_profile = json.load(f)
        
        if "like_movies" not in user_profile:
            return
        movie_list = user_profile["like_movies"][-5:]
        # movie_list = []
        conditions = dict()
        for attr in realted_attr_list:
            if attr not in known_tag_list:
                continue
            conditions[attr] = message.get("known_tag_dict")[attr]
        # conditions = self._generate_condition(conditions)
        # print(conditions)
        # print(movie_list)
        messages = [{"role":"system", "content": sys_prompt.format(movie_list=movie_list, conditions=conditions)}]
        # print(messages)
        request_timeout = 20
        for attempt in Retrying(
                reraise=True,
                retry=retry_if_not_exception_type((openai.error.InvalidRequestError)),
                wait=my_wait_exponential(min=1, max=60), stop=(my_stop_after_attempt(8))
        ):
            with attempt:
                response = openai.ChatCompletion.create(
                                model=self.conf["model_name"],
                                messages=messages,
                                temperature=0,
                                request_timeout=50
                            )
            request_timeout = min(300, request_timeout * 2)
        print(response.choices[0].message["content"])
        corr_movies = fix_and_parse_json(response.choices[0].message["content"])
        t_dict = dict()
        if corr_movies == None:
            return
        for movie in corr_movies:
            if movie in movie_list:
                t_dict[movie] = corr_movies[movie]
                if movie in message.get('target_items'):
                    raise Exception("Movie in target_items")
        if len(t_dict) == 0:
            return
        reply = self._generate_reply(conditions, t_dict)
        message['reply'] = reply
        message['to_plugin4'] = False
        
        st_write("plugin5", {"reply": message['reply']})
        