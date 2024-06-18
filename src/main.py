from crs_agent import CRSAgent
from user_sim_agent import UserSimAgent
import autogen
from config import set_key
from utils import *


set_key()

if __name__ == '__main__':
    config_list = autogen.config_list_from_json(
        "OAI_CONFIG_LIST",
        filter_dict={
            "model": ["gpt-3.5-turbo-0613"],
        },
    )
    crs_agent = CRSAgent(
        name="crs_agent",
        llm_config={"config_list": config_list},
        max_turn=10,
    )
    user_sim_agent = UserSimAgent(
        name="user_sim_agent",
        llm_config={"config_list": config_list},
        max_turn=10,
        human_input_mode="ALWAYS"
    )
    user_sim_agent.reset(user_id=1, target_item="Toy Story(1995)")
    crs_agent.initiate_chat(user_sim_agent,
                         message='Hello, how can i help you?', 
                         )
    save_to_json(user_sim_agent.message, filter_keys=['target_items', 'info_dict', 'oai_messages', 'turn', 'real_time_preference_list', 
                                                      'init_known_tag_dict', 'init_unknown_tag_dict', 'known_tag_dict', 'unknown_tag_dict',
                                                      ])