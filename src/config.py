import os
import openai


def set_key():
    os.environ["OPENAI_API_KEY"] = "xxx"
    openai.api_key = "xxx"
    openai.api_base = "xxx"
