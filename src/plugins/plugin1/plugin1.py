from src.plugins import *
import openai
import re
import os
import json


sys_prompt = """
I want you to act as an agent. You will act as a movie taste analyst roleplaying the user using the first person pronoun "I".
"""

prompt = """
Given a user's rating history:

user gives a rating of 1 for following movies: <INPUT1>
user gives a rating of 2 for following movies: <INPUT2>
user gives a rating of 3 for following movies: <INPUT3>
user gives a rating of 4 for following movies: <INPUT4>
user gives a rating of 5 for following movies: <INPUT5>

My first request is "I need help creating movie taste for a user given the movie-rating history. (in no particular order)"  Generate as many TASTE-REASON pairs as possible, taste should focus on the movies' genres.
Strictly follow the output format below:

TASTE: <-descriptive taste->
REASON: <-brief reason->

TASTE: <-descriptive taste->
REASON: <-brief reason->
.....

Secondly, analyze user tend to give what kinds of movies high ratings, and tend to give what kinds of movies low ratings.
Strictly follow the output format below:
HIGH RATINGS: <-conclusion of movies of high ratings(above 3)->
LOW RATINGS: <-conclusion of movies of low ratings(below 2)->
Answer should not be a combination of above two parts and not contain other words and should not contain movie names.

"""


@register(
    name="Plugin1",
    enabled=True,
)
class Plugin1(Plugin):
    def __init__(self):
        super().__init__()
        self.conf = super().load_config()
        self.handlers["user_profile_init"] = self.generate_user_profile
    
    def _get_user_rating_history(self, user_id, ratings, movies_info)->dict:
        user_rating_dict = dict()
        for index, row in ratings[ratings["user_id"]==user_id].iterrows():
            if row['ratings'] not in user_rating_dict:
                user_rating_dict[row['ratings']] = []
            user_rating_dict[row['ratings']].append(movies_info[movies_info["movies_id"]==row["movies_id"]]["title"].values[0])
        return user_rating_dict

    def _get_user_rating_list(self, user_rating_dict, k):
        res_dict = dict()
        for rating in user_rating_dict:
            if len(user_rating_dict[rating]) >= k:
                res_dict[rating] = user_rating_dict[rating][:k]
            else:
                res_dict[rating] = user_rating_dict[rating]
        return res_dict
    
    def _get_completion(self, model_name):
        messages = [{"role":"user", "content" : prompt}, {"role":"system", "content" : sys_prompt}]
        response = openai.ChatCompletion.create(
                    model=model_name,
                    messages=messages,
                    temperature=0,
                    request_timeout=50
                )
        return response.choices[0].message["content"]

    def _extract_taste_reason(self, s):
        taste = re.findall(r'TASTE:(.+)', s)
        reason = re.findall(r'REASON:(.+)', s)
        return taste, reason
    
    def check_user_profile(self, user_id: str) -> bool:
        folder_path = "./user_profile/"
        file_name = f"{user_id}.json"
        file_path = os.path.join(folder_path, file_name)
        
        if os.path.exists(file_path):
            return True
        else:
            return False
    
    def generate_user_profile(self, message: Message):
        user_id = message.content
        ratings = message.get("ratings")
        movies_info = message.get("movies_info")
        # users_info = message.get("users_info")
        
        user_rating_dict = self._get_user_rating_history(user_id, ratings, movies_info)
        # user_rating_dict = self._get_user_rating_list(user_rating_dict, 20)
        global prompt
        for rating in user_rating_dict:
            if rating == 1:
                prompt = prompt.replace("<INPUT1>", ','.join(list(user_rating_dict[rating]))) if len(user_rating_dict[rating]) > 0 else prompt.replace("<INPUT1>", "None")
            elif rating == 2:
                prompt = prompt.replace("<INPUT2>", ','.join(list(user_rating_dict[rating]))) if len(user_rating_dict[rating]) > 0 else prompt.replace("<INPUT2>", "None")
            elif rating == 3:
                prompt = prompt.replace("<INPUT3>", ','.join(list(user_rating_dict[rating]))) if len(user_rating_dict[rating]) > 0 else prompt.replace("<INPUT3>", "None")
            elif rating == 4:
                prompt = prompt.replace("<INPUT4>", ','.join(list(user_rating_dict[rating]))) if len(user_rating_dict[rating]) > 0 else prompt.replace("<INPUT4>", "None")
            else:
                prompt = prompt.replace("<INPUT5>", ','.join(list(user_rating_dict[rating]))) if len(user_rating_dict[rating]) > 0 else prompt.replace("<INPUT5>", "None")
        
        response = self._get_completion(self.conf.get("model_name"))
        taste, reason = self._extract_taste_reason(response)
        
        if not self.check_user_profile(user_id):
            user_profile = dict()
        else:
            with open("./user_profile/"+str(user_id)+".json", "r") as f:
                user_profile = json.load(f)
                
        taste_list = []
        for i in range(len(taste)):
            taste_list.append({"taste": taste[i], "reason": reason[i]})
        user_profile["taste"] = taste_list
        
        with open("./user_profile/"+str(user_id)+".json", "w") as f:
            json.dump(user_profile, f, indent=4)