from src.plugins import *


sys_prompt = """
You are an excellent assiatant, you will act as a user chatting with a movie expert to get some movie recommendations.

You only focus on the following aspects of the movie: {tag_list}

When the expert asks you about your preference about other aspects, you should express you don't care about them.

Your current movies preference is: {real_time_preference}

Based on your current preference, chat with the expert to get some movie recommendations. Just answer the expert's questions and don't ask for recommendations directly.

"""

@register(
    name="plugin4",
    enabled=True,
)
class Plugin4(Plugin):
    def __init__(self):
        super().__init__()
        self.conf = super().load_config()
        self.handlers["handle_message"] = self.handle_message
        
    def handle_message(self, message: Message) -> None:
        if message.get("intent") != "ask":
            return
        
        print(message.get("to_plugin4"))
        if message.get('to_plugin4') == False:
            return
        
        real_time_preference = message.get("real_time_preference")
        known_tag_list = message.get("known_tag_list")
        unknown_tag_list = message.get("unknown_tag_list")
        tag_list = known_tag_list + unknown_tag_list
        
        messages = [{"role": "system", "content": sys_prompt.format(tag_list=tag_list, real_time_preference=real_time_preference)}] + [message["oai_messages"][-1]]
        print("hhh", messages)

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
        reply = response.choices[0].message["content"]
        message['reply'] = reply
        st_write("plugin4", {"reply": message['reply']})
        