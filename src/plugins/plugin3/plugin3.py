from src.plugins import *
import random

sys_prompt = """
You are an movie expert, you are going to generate a movie basic information when given a movie title.
"""

prompt = """
The movie title is: {movie_title}
My request is "I need help generating the given movie basic information, including the following attributes: {attr_list}"

Strictly follow the output format below:
title: <the movie title>
genres: <the movie genres>
...
"""

release_date_prompt = """
Express the film release date {date} in terms of years, e.g. 90s

Strictly follow the output format below:
OUTPUT: <-years->
"""

runtime_prompt = """
Given a movie duration {duration}, express the approximate duration in hours only.

Some example: 140min -> about 2h, 160min -> 2h ~ 3h, 180min -> about 3h.

Strictly follow the output format below:
OUTPUT: <-fuzzified duration->
"""

real_time_preference_generate_prompt = """
You are an excellent assiatant, you will act as a user who is looking for some movies to watch. Please roleplay the user using the first person pronoun "I".

Your current movie preference is: {preference}

You need generate a demand based on your preference.

Strictly follow the output format below:
DEMAD: <-descriptive demand->
"""

@register(
    name="plugin3",
    enabled=True,
)
class Plugin3(Plugin):
    def __init__(self):
        super().__init__()
        self.conf = super().load_config()
        self.handlers["real_time_preference_init"] = self.real_time_preference_init
    
    def _get_movie_information(self, movie_title):
        attr_list = self.conf["attr_list"]
        messages = [{"role":"system", "content" : sys_prompt}, {"role":"user", "content" : prompt.format(movie_title=movie_title, attr_list=attr_list)}]
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
        # print(response.choices[0].message["content"])
        t_list = response.choices[0].message["content"].split("\n")
        res = dict()
        for t in t_list:
            if ':' not in t:
                continue
            t = t.split(":")
            res[t[0]] = t[1].strip()
        return res
    
    def _map_release_date(self, release_date):
        messages = [{"role": "system", "content": "You are an excellent assistant."}, {"role": "user", "content": release_date_prompt.format(date=release_date)}]
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
        # return response.choices[0].message["content"].split(":")[1].strip()
        return response.choices[0].message["content"].replace("OUTPUT:", "").strip()
    
    def _map_runtime(self, runtime):
        messages = [{"role": "system", "content": "You are an excellent assistant."}, {"role": "user", "content": runtime_prompt.format(duration=runtime)}]
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
        # return response.choices[0].message["content"].split(":")[1].strip()
        return response.choices[0].message["content"].replace("OUTPUT:", "").strip()
    
    def _generate_real_time_preference(self, preference):
        messages = [{"role": "system", "content": real_time_preference_generate_prompt.format(preference=preference)}]
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
                    request_timeout=50,
                    max_tokens=8192,
                )
            request_timeout = min(300, request_timeout * 2)
        return response.choices[0].message["content"]
    
    def real_time_preference_init(self, message: Message) -> None:
        info_dict = self._get_movie_information(message.content)
        # print(info_dict)
        # 目前策略随机选择k个属性作为用户偏好，其余则不关心
        tag_list = list(info_dict.keys())
        # 脱敏的消融实验
        if "release date" in tag_list:
            info_dict["release date"] = self._map_release_date(info_dict["release date"])
        if "runtime" in tag_list:
            info_dict["runtime"] = self._map_runtime(info_dict["runtime"])
        if "actors" in tag_list:
            info_dict["actors"] = info_dict["actors"].split(",")[0]
        if "director" in tag_list:
            info_dict["director"] = info_dict["director"].split(",")[0]
        print(info_dict)
        
        tag_list.remove("title")
        k1 = self.conf["k1"]
        k2 = self.conf["k2"]
        # like_tag_list = random.sample(tag_list, k1 + k2)
        # like_tag_list = ['genres', 'actors', 'runtime', 'director', 'release date']
        like_tag_list = tag_list
        preference = dict()
        unknown_tag_dict = dict()
        for tag in like_tag_list[:k1]:
            preference[tag] = info_dict[tag]
        for tag in like_tag_list[k1:]:
            unknown_tag_dict[tag] = info_dict[tag]
        
        real_time_preference = self._generate_real_time_preference(preference)
        
        message["info_dict"] = info_dict
        message["known_tag_list"] = like_tag_list[:k1]
        message["known_tag_dict"] = preference
        message["init_known_tag_dict"] = preference.copy()
        message["unknown_tag_list"] = like_tag_list[k1:]
        message["unknown_tag_dict"] = unknown_tag_dict
        message["init_unknown_tag_dict"] = unknown_tag_dict.copy()
        message["real_time_preference"] = real_time_preference.replace("DEMAND:", "").strip()
        message["real_time_preference_list"] = [message["real_time_preference"]]
        
        st_write("plugin3", {"info_dict": message["info_dict"], 
                            "known_tag_list": message["known_tag_list"], 
                            "known_tag_dict": message["known_tag_dict"],
                            "init_known_tag_dict": message["init_known_tag_dict"],
                            "unknown_tag_list": message["unknown_tag_list"],
                            "unknown_tag_dict": message["unknown_tag_dict"],
                            "init_unknown_tag_dict": message["init_unknown_tag_dict"],
                            "real_time_preference": message["real_time_preference"],
                            "real_time_preference_list": message["real_time_preference_list"]
        })  