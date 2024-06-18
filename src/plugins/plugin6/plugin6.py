from src.plugins import *


intent_understanding_prompt = """
You are an excellent assistant. You will act as a user chatting with a movie expert.

The expert has three actions: 
1. ask: Ask some questions about your preference about movies, such as genre, director, etc.
2. recommend: Recommended films for you.
3. chit-chat: Chat with you about movies or chat with you about other topics.

You need to understand the expert's intent, i.e. ask or recommend.

The expert said: "I think you're going to love Toy Story, have you seen it?"
OUTPUT: recommend
REASON: The expert recommended Toy Story to me, although he asked me if I had seen it, the question don't related to my preference.

The expert said: "What kind of films do you like?"
OUTPUT: ask
REASON: The expert asked me about my preference about movie genres.

The expert said: {message}
"""

judge_prompt = """
You are an excellent assistant.

Now given a question: {question}, select the element that is related to the question from the element list: {element_list}.

If there is no related element, choose "NONE".

Strictly follow the output format below:
OUTPUT: [element1, element2, ...]
"""

@register(
    name="plugin6",
    enabled=True,
)
class Plugin6(Plugin):
    '''
    该插件目前作为消息处理的第一步，作用为理解对方意图，可以当作思考的过程
    '''
    def __init__(self):
        super().__init__()
        self.conf = super().load_config()
        self.handlers["handle_message"] = self.handle_message
    
    def _intent_understanding(self, message):
        messages = [{"role": "system", "content": intent_understanding_prompt.format(message=message)}]
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
        response = response.choices[0].message["content"].split("\n")[0]
        if response.find("OUTPUT: ") == -1:
            return response
        return response.split(":")[1].strip()
    
    def _judge_attr(self, question):
        element_list = self.conf["attr_list"]
        messages = [{"role":"system", "content": judge_prompt.format(question=question, element_list=element_list)}]
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
        attr_list = response.choices[0].message["content"].replace("OUTPUT:", "").strip()[1:-1].split(", ")
        attr_list = [attr.strip()[1:-1] for attr in attr_list if not attr[0].isalpha()]
        return attr_list
    
    def handle_message(self, message: Message) -> None:
        content = message.get("content")
        intent = self._intent_understanding(content)
        print(f"intent:{intent}")
        if intent == "recommend":
            message["intent"] = "recommend"
        elif intent == "ask":
            message["intent"] = "ask"
            realted_attr_list = self._judge_attr(content)
            message["realted_attr_list"] = realted_attr_list
            print(f"intent: {intent}, realted_attr_list: {realted_attr_list}")
        elif intent == "chit-chat":
            message["intent"] = "chit-chat"
        else:
            message["intent"] = "chit-chat"
            # raise ValueError(f"Unknown intent: {intent}")
        
        st_write("plugin6", {"intent": message["intent"],
                             "realted_attr_list": message.get("realted_attr_list")
                             })