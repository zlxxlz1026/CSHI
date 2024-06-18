from src.plugins import *
import random


preference_init_prompt = """
You are an excellent assiatant, you will act as a user who is looking for some movies to watch. Please roleplay the user using the first person pronoun "I".

Your current movie preference is: {preference}

You need generate a reply based on your preference and the conversation history, but you should remember that you are a seeker, not a recommender. Don't recommend movies.
"""

@register(
    name="plugin9",
    enabled=True,
)
class Plugin9(Plugin):
    def __init__(self):
        super().__init__()
        self.conf = super().load_config()
        self.handlers["handle_message"] = self.handle_message
    
    def _get_init_preference(self, preference, message):
        messages = message['oai_messages'] + [{"role": "system", "content": preference_init_prompt.format(preference=preference)}]
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
        return response.choices[0].message["content"]
    
    def handle_message(self, message: Message) -> None:
        if message.get("intent") != "chit-chat":
            return
        known_tag_list = message.get("known_tag_list")
        known_tag_dict = message.get("known_tag_dict")
        attr = random.choice(known_tag_list)
        message['reply'] = self._get_init_preference(f"{attr}: {known_tag_dict[attr]}", message)