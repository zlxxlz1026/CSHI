import os
import json
from tenacity import Retrying, retry_if_not_exception_type, _utils
import typing
from tenacity.stop import stop_base
from tenacity.wait import wait_base
import openai


def save_to_json(content, filter_keys=None):
    if 'user_id' not in content or 'target_items' not in content:
        raise Exception("user_id or target_items not in content")
    folder_path = f"./output/{content['user_id']}/"
    file_name = f"{content['target_items'][0]}.json"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    t_dict = dict()
    if filter_keys is not None:
        for key in filter_keys:
            t_dict[key] = content[key]
        
    with open(os.path.join(folder_path, file_name), 'w', encoding='utf-8') as f:
        json.dump(t_dict, f, ensure_ascii=False, indent=4)
        

def split_test(k=5):
    file_path = './user_profile'
    file_list = os.listdir(file_path)
    for file_name in file_list:
        with open(os.path.join(file_path, file_name), 'r', encoding='utf-8') as f:
            content = json.load(f)
            content['test_items'] = content['like_movies'][-k:]
            content['like_movies'] = content['like_movies'][:-k]
            
        with open(os.path.join(file_path, file_name), 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)
    

class my_wait_exponential(wait_base):
    def __init__(
        self,
        multiplier: typing.Union[int, float] = 1,
        max: _utils.time_unit_type = _utils.MAX_WAIT,  # noqa
        exp_base: typing.Union[int, float] = 2,
        min: _utils.time_unit_type = 0,  # noqa
    ) -> None:
        self.multiplier = multiplier
        self.min = _utils.to_seconds(min)
        self.max = _utils.to_seconds(max)
        self.exp_base = exp_base

    def __call__(self, retry_state: "RetryCallState") -> float:
        if retry_state.outcome == openai.error.Timeout:
            return 0

        try:
            exp = self.exp_base ** (retry_state.attempt_number - 1)
            result = self.multiplier * exp
        except OverflowError:
            return self.max
        return max(max(0, self.min), min(result, self.max))


class my_stop_after_attempt(stop_base):
    """Stop when the previous attempt >= max_attempt."""

    def __init__(self, max_attempt_number: int) -> None:
        self.max_attempt_number = max_attempt_number

    def __call__(self, retry_state: "RetryCallState") -> bool:
        if retry_state.outcome == openai.error.Timeout:
            retry_state.attempt_number -= 1
        return retry_state.attempt_number >= self.max_attempt_number