import streamlit as st
import os
import json
import openai
from config import set_key
from src.utils import *


set_key()

sys_prompt = """You are a seeker chatting with a recommender for recommendation. Your target items: {target_item}. You must follow the instructions below during chat.
Here is the information about target item: {item_info}.
If the recommender recommend {target_item}, you should accept.
If the recommender recommend other items, you should refuse them and provide the information about {target_item}. You should never directly tell the target item title.
If the recommender asks for your preference, you should provide the information about {target_item}. You should never directly tell the target item title.
"""

sys_prompt1 = """You are a seeker chatting with a recommender for recommendation. Your target items: {target_item}. You must follow the instructions below during chat.
If the recommender recommend {target_item}, you should accept.
If the recommender recommend other items, you should refuse them and provide the information about {target_item}. You should never directly tell the target item title.
If the recommender asks for your preference, you should provide the information about {target_item}. You should never directly tell the target item title.
"""

prompt = """
You are an movie expert, you are going to generate a movie basic information when given a movie title.

The movie title is: {target_item}
My request is "I need help generating the given movie basic information, including genres, director, runtime, release date, actors, etc."

Strictly follow the output format below:
title: <the movie title>
genres: <the movie genres>
...
"""

def get_item_info(target_item):
    messages = [{"role": "system", "content": prompt.format(target_item=target_item)}]
    response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
            temperature=0,
            request_timeout=50
        )
    t_list = response.choices[0].message["content"].split("\n")
    res = dict()
    for t in t_list:
        t = t.split(":")
        res[t[0]] = t[1].strip()
    tag_list = list(res.keys())
    if "actors" in tag_list:
        res["actors"] = res["actors"].split(",")[0]
    if "director" in tag_list:
        res["director"] = res["director"].split(",")[0]
    return res

def get_llm_response1(target_item):
    messages = [{"role": "system", "content": sys_prompt1.format(target_item=target_item)}]
    for message in st.session_state.messages:
        messages.append(message)
    # messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}]
    # print(messages)
    for attempt in Retrying(
        reraise=True,
        retry=retry_if_not_exception_type((openai.error.InvalidRequestError)),
        wait=my_wait_exponential(min=1, max=60), stop=(my_stop_after_attempt(8))
    ):
        with attempt:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-0613",
                messages=messages,
                temperature=0,
                request_timeout=50
            )
        request_timeout = min(300, request_timeout * 2)
    # print(response.choices[0].message["content"])
    return response.choices[0].message["content"]

def get_llm_response(target_item, target_item_info):
    messages = [{"role": "system", "content": sys_prompt.format(target_item=target_item, item_info=target_item_info)}]
    for message in st.session_state.messages:
        messages.append(message)
    # messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}]
    # print(messages)
    for attempt in Retrying(
        reraise=True,
        retry=retry_if_not_exception_type((openai.error.InvalidRequestError)),
        wait=my_wait_exponential(min=1, max=60), stop=(my_stop_after_attempt(8))
    ):
        with attempt:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-0613",
                messages=messages,
                temperature=0,
                request_timeout=50
            )
        request_timeout = min(300, request_timeout * 2)
    # print(response.choices[0].message["content"])
    return response.choices[0].message["content"]

# App title
st.set_page_config(page_title="Prompt-based Chatbot",
                   layout="wide",
                   page_icon=":robot_face:")

st.title("Prompt-based Chatbot")
st.caption("🚀 User simulator for movie recommendations.")

st.session_state.last_message = ""

with st.sidebar:
    col1, col2, col3 = st.columns(3)
    with col1:
        file_list = os.listdir('./user_profile/')
        file_list = [file_name.split('.')[0] for file_name in file_list]
        user_id = st.selectbox('User ID:', file_list)
        with open(os.path.join('./user_profile/', f"{user_id}.json"), 'r', encoding='utf-8') as f:
            long_preference = json.load(f)
    with col2:
        test_items = long_preference['test_items']
        st.session_state.target_item = st.selectbox('Target Item:', test_items)
    with col3:
        mode = st.selectbox('Mode', ['Manual', 'Auto'])
    with st.form(key='my_form'):
        text_input = st.text_area(label='**Enter your prompt：**', height=300, key='text_input', value=sys_prompt)
        submit_button = st.form_submit_button(label='Submit', use_container_width=True)
        if submit_button:
            st.session_state.target_item_info = get_item_info(st.session_state.target_item)
            st.session_state.messages = [{"role": "user", "content": "How can i help you today?"}]
            # sys_prompt = text_input
            # st.session_state.last_message = get_llm_response(st.session_state.target_item, st.session_state.target_item_info)
            st.session_state.last_message = get_llm_response1(st.session_state.target_item)

if 'messages' not in st.session_state:
    st.session_state.messages = []
        
# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# User-provided prompt
if prompt := st.chat_input(disabled=(mode != 'Manual')):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.spinner("Thinking..."):
        # st.session_state.last_message = get_llm_response(st.session_state.target_item, st.session_state.target_item_info)
        st.session_state.last_message = get_llm_response1(st.session_state.target_item)
        
# Generate a new response if last message is not from assistant
if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        response = st.session_state.last_message
        st.write(response)
    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)