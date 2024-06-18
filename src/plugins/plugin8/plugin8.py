from src.plugins import *


real_time_preference_generate_prompt = """
You are an excellent assiatant, you will act as a user who is looking for some movies to watch. Please roleplay the user using the first person pronoun "I".

Your current movie preference is: {preference}

You need generate a demand based on your preference.

Strictly follow the output format below:
DEMAD: <-descriptive demand->
"""

preference_guide_prompt = """
You are an excellent assistant. You are chatting with a movie expert for movie recommendations.

You don't like none of the movies recommended by the expert. Your thoughts are as follows: {reject_reply}

But you want the next recommendations will contain the following information he mentioned: {acc_dict}

You need generate a smooth and natural declarative reply combined with your thoughts and the information you are interested in.
"""

@register(
    name="plugin8",
    enabled=True,
)
class Plugin8(Plugin):
    def __init__(self):
        super().__init__()
        self.conf = super().load_config()
        self.handlers["handle_message"] = self.handle_message
    
    def _update_real_time_preference(self, preference):
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
                    request_timeout=50
                )
            request_timeout = min(300, request_timeout * 2)
        return response.choices[0].message["content"]
    
    def _get_reply(self, reject_reply, acc_dict):
        messages = [{"role": "system", "content": preference_guide_prompt.format(reject_reply=reject_reply, acc_dict=acc_dict)}]
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
        return response.choices[0].message["content"]
    
    def handle_message(self, message):
        if not (message.get("intent") == "recommend" and message.get("result") == "rej"):
            return
        content = message.get("content")
        unknown_tag_dict = message.get("unknown_tag_dict")
        known_tag_dict = message.get("known_tag_dict")
        acc_dict = dict()
        print(f"known_tag_dict: {known_tag_dict}, unknown_tag_dict: {unknown_tag_dict}")
        for tag, value in unknown_tag_dict.items():
            if value in content:
                acc_dict[tag] = value
                known_tag_dict[tag] = value
        if len(acc_dict) == 0:
            return
        for tag in acc_dict.keys():
            del unknown_tag_dict[tag]
        print(f"known_tag_dict: {known_tag_dict}, unknown_tag_dict: {unknown_tag_dict}")
        reject_reply = message.get("reply")
        reply = self._get_reply(reject_reply, acc_dict)
        message["reply"] = reply        
        
        message["unknown_tag_dict"] = unknown_tag_dict
        message["unknown_tag_list"] = list(unknown_tag_dict.keys())
        message["known_tag_dict"] = known_tag_dict
        message["known_tag_list"] = list(known_tag_dict.keys())
        
        real_time_preference = self._update_real_time_preference(known_tag_dict)
        message["real_time_preference"] = real_time_preference.replace("DEMAND:", "").strip()
        message["real_time_preference_list"].append(message["real_time_preference"])

        st_write("plugin8", {"reply": message['reply'], "real_time_preference": message["real_time_preference"]})