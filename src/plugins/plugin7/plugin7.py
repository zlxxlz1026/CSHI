from src.plugins import *


reject_prompt = """
You are an excellent assistant. You will act as a user chatting with a movie expert for movie recommendations.

Your current movies preference is: {real_time_preference}

The history of your conversation with the expert is as follows:
{history}

Now the expert recommends you some movies: {recommend_content}

But you don't like any of the movies recommended by the expert, you need to tell the expert that you don't like any of them.

You can base on your preference to generate a smooth and natural reply, but don't say too much preference information.

Strictly follow the output format below:
<-your reply->
"""

accept_prompt = """
You are an excellent assistant. You will act as a user chatting with a movie expert for movie recommendations.

Your current movies preference is: {real_time_preference}

The history of your conversation with the expert is as follows:
{history}

Now the expert recommends you some movies: {recommend_content}

You are interested in {target_item} in the recommendation, you need to accept the recommendation and show your willingness to try {target_item}, then end the conversation.

Strictly follow the output format below:
<-your reply->
"""

@register(
    name="plugin7",
    enabled=True,
)
class Plugin7(Plugin):
    '''
    该插件处理推荐逻辑。
    '''
    def __init__(self):
        super().__init__()
        self.conf = super().load_config()
        self.handlers["handle_message"] = self.handle_message
    
    def _get_conversation_history(self, oai_messages) -> str:
        history = ""
        for message in oai_messages:
            if message["role"] == "assistant":
                history += "You: " + message["content"] + "\n"
            elif message["role"] == "user":
                history += "Expert: " + message["content"] + "\n"
        return history
    
    def _generate_reply(self, real_time_preference, conv_history, recommend_content, target_items):
        acc_list = list()
        for item in target_items:
            item = item.split("(")[0].strip()
            if recommend_content.lower().find(item.lower()) != -1:
                acc_list.append(item)
        if len(acc_list) > 0:
            result = 'acc'
            prompt = accept_prompt.format(real_time_preference=real_time_preference, history=conv_history, recommend_content=recommend_content, target_item=acc_list)
        else:
            result = 'rej'
            prompt = reject_prompt.format(real_time_preference=real_time_preference, history=conv_history, recommend_content=recommend_content)
        messages = [{"role": "system", "content": prompt}]
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
        # return result, response.choices[0].message["content"].split(":")[1].strip()
        return result, response.choices[0].message["content"]
    
    def handle_message(self, message: Message) -> None:
        if message.get("intent") != "recommend":
            return
        
        real_time_preference = message.get("real_time_preference")
        conv_history = self._get_conversation_history(message.get("oai_messages"))
        recommend_content = message.get("content")
        target_items = message.get("target_items")
        result, reply = self._generate_reply(real_time_preference, conv_history, recommend_content, target_items)
        message["reply"] = reply
        message["result"] = result
        
        st_write("plugin7", {"reply": message['reply'], "result": message["result"]})
        