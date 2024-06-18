import streamlit as st
import os
import time 
import autogen
from utils import *
from config import set_key
from crs_agent import CRSAgent
from user_sim_agent import UserSimAgent
# from plugins import pm

set_key()


config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-3.5-turbo-0613"],
    },
)
if crs_agent := st.session_state.get("crs_agent", None) is None:
    st.session_state.crs_agent = CRSAgent(
        name="crs_agent",
        llm_config={"config_list": config_list},
        max_turn=10,
    )
if user_sim_agent := st.session_state.get("user_sim_agent", None) is None:
    st.session_state.user_sim_agent = UserSimAgent(
        name="user_sim_agent",
        llm_config={"config_list": config_list},
        max_turn=10,
    )


# App title
st.set_page_config(page_title="🤖💬 CSHI-Based Chatbot",
                   layout="wide",
                   page_icon=":robot_face:")

st.title("🤖💬 CSHI-Based Chatbot")
st.caption("🚀 User simulator for movie recommendations.")

def param_init():
    # st.subheader('📝 Plugin param init')
    selected_model = st.selectbox('Choose a model', ['gpt-3.5-turbo-0613', 'gpt-4-0613'], key='selected_model')
    col1, col2 = st.columns(2)
    with col1:
        k1 = st.number_input('k1', min_value=1, max_value=10, value=3, step=1, key='k1',
                         help='Choose k1 attribute to generate user real-time preference')
    with col2:
        k2 = st.number_input('k2', min_value=0, max_value=10, value=2, step=1, key='k2',
                         help='Choose k2 attribute to simluate user unknown preference')
    t = st.multiselect('Choose attr', ["title", "genres", "director", "actors", "release date", "runtime", "rating", "language"], key='attrs'
                   , default=["title", "genres", "director", "actors", "release date", "runtime", "rating", "language"])
    # print(pm.plugins_config)

def information_output():
    check_target_item_info = st.checkbox('Show Target Item Info', value=False)
    if check_target_item_info:
        if 'target_item_info' not in st.session_state:
            st.warning('Please init param first!', icon='⚠️')
        else:
            st.write(st.session_state.target_item_info)
    check_long_preference = st.checkbox('Show User Long Term Preference', value=False)
    if check_long_preference:
        if 'long_preference' not in st.session_state:
            st.warning('Please init param first!', icon='⚠️')
        else:
            st.write(st.session_state.long_preference)
    check_real_time_preference = st.checkbox('Show User Real Time Preference', value=False)
    if check_real_time_preference:
        placeholder = st.empty()
        if 'real_time_preference' not in st.session_state:
            placeholder.warning('Please init param first!', icon='⚠️')
        else:
            placeholder.markdown(f":red[Real time preference:]:blue[{st.session_state.real_time_preference}]")
    check_known_preference = st.checkbox('Show User Known Preference', value=False)
    if check_known_preference:
        placeholder = st.empty()
        if 'known_preference' not in st.session_state:
            placeholder.warning('Please init param first!', icon='⚠️')
        else:
            placeholder.write(st.session_state.known_preference)
    check_unknown_preference = st.checkbox('Show User Unknown Preference', value=False)
    if check_unknown_preference:
        placeholder = st.empty()
        if 'unknown_preference' not in st.session_state:
            placeholder.warning('Please init param first!', icon='⚠️')
        else:
            placeholder.write(st.session_state.unknown_preference)
def plugin_output():
    param = st.text_input('Enter **plugin name** or **object name** to be observed:', key='object')
    placeholder = st.empty()
    print(param)
    if param != '':
        if param not in st.session_state:
            placeholder.warning("Can't find the object, please check!", icon='⚠️')
        else:
            placeholder.write(st.session_state[param])

if 'messages' not in st.session_state:
    st.session_state.messages = []

# Replicate Credentials
with st.sidebar:
    # st.title(':blue[Param:]')
    with st.expander("🔒 Credentials", expanded=False):
        if 'openai_api_key' in st.secrets:
            st.success('API key already provided!', icon='✅')
            openai_api_key = st.secrets['openai_api_key']
        else:
            openai_api_key = st.text_input('Enter OpenAI API key:', type='password')
            openai_api_base = st.text_input('(Optional) Enter OpenAI API base:', value='https://api.openai.com')
            if not (openai_api_key.startswith('sk-') and len(openai_api_key)==51):
                st.warning('Please enter your credentials!', icon='⚠️')
            else:
                st.success('Proceed to entering your prompt message!', icon='👉')
    col1, col2, col3 = st.columns(3)
    with col1:
        file_list = os.listdir('./user_profile/')
        file_list = [file_name.split('.')[0] for file_name in file_list]
        user_id = st.selectbox('User ID:', file_list)
        with open(os.path.join('./user_profile/', f"{user_id}.json"), 'r', encoding='utf-8') as f:
            long_preference = json.load(f)
    with col2:
        test_items = long_preference['test_items']
        target_item = st.selectbox('Target Item:', test_items)
    with col3:
        mode = st.selectbox('Mode', ['Manual', 'Auto'])
    
    tab1, tab2, tab3 = st.tabs(['📖 Param init', '📖Information', '📖 Plugin output'])
    with tab1:   
        with st.form(key='my_form', border=False):
            param_init()
            submitted = st.form_submit_button(label='Submit', type="primary", use_container_width=True)
            if submitted:
                st.session_state.messages = [{"role": "user", "content": "How can i help you today?"}]
                st.session_state.user_sim_agent.reset(int(user_id), target_item)
                st.session_state.crs_agent._prepare_chat(st.session_state.user_sim_agent, clear_history=True)
                st.session_state.long_preference = long_preference
                if mode == 'Manual':
                    st.session_state.crs_agent.stop_reply_at_receive(st.session_state.user_sim_agent)
                    st.session_state.crs_agent.send(message='Hello, how can i help you?', recipient=st.session_state.user_sim_agent)
    with tab2:
        information_output()
    with tab3:
        plugin_output()
    
    st.divider()
    os.environ['openai_api_key'] = openai_api_key
    os.environ['openai_api_base'] = openai_api_base


# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])


def clear_chat_history():
    st.session_state.messages = []
st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

# User-provided prompt
if prompt := st.chat_input(disabled=(mode != 'Manual')):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.spinner("Thinking..."):
        print("test")
        st.session_state.crs_agent.send(prompt, st.session_state.user_sim_agent)

# Generate a new response if last message is not from assistant
if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        response = st.session_state.crs_agent.last_message(st.session_state.user_sim_agent)["content"]
        st.write(response)
    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)