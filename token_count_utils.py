import logging
import json
import tiktoken
import re


logger = logging.getLogger(__name__)


def get_max_token_limit(model: str = "gpt-3.5-turbo-0125") -> int:
    model = re.sub(r"^gpt\-?35", "gpt-3.5", model)
    model = re.sub(r"^gpt4", "gpt-4", model)
    
    max_token_limit = {
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-0301": 4096,
        "gpt-3.5-turbo-0613": 4096,
        "gpt-3.5-turbo-instruct": 4096,
        "gpt-3.5-turbo-16k": 16385,
        "gpt-3.5-turbo-16k-0613": 16385,
        "gpt-3.5-turbo-1106": 16385,
        "gpt-3.5-turbo-0125": 16385,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-32k-0314": 32768,  # deprecate in Sep
        "gpt-4-0314": 8192,  # deprecate in Sep
        "gpt-4-0613": 8192,
        "gpt-4-32k-0613": 32768,
        "gpt-4-1106-preview": 128000,
        "gpt-4-0125-preview": 128000,
        "gpt-4-turbo-preview": 128000,
        "gpt-4-vision-preview": 128000,
    }
    return max_token_limit[model]


def percentile_used(input, model="gpt-3.5-turbo-0125"):
    return count_token(input) / get_max_token_limit(model)


def token_left(input, model="gpt-3.5-turbo-0125"):
    return get_max_token_limit(model) - count_token(input)


def count_token(input, model="gpt-3.5-turbo-0125"):
    if isinstance(input, str):
        return _num_token_from_text(input, model=model)
    elif isinstance(input, list):
        return _num_token_from_messages(input, model=model)
    else:
        raise ValueError(f"Unknown input type: {type(input)}")


def _num_token_from_text(text: str, model="gpt-3.5-turbo-0125") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning(f"Model {model} not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def _num_token_from_messages(messages: list, model="gpt-3.5-turbo-0125") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        logger.info("gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
        return _num_token_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        logger.info("gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return _num_token_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""_num_token_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            if value is None:
                continue
            
            if not isinstance(value, str):
                try:
                    value = json.dumps(value)
                except TypeError:
                    logger.warning(
                        f"Value {value} is not a string and cannot be converted to json. It is a type: {type(value)} Skipping."
                    )
                    continue
            
            num_tokens += len(encoding.encode(value))
            if key == 'name':
                num_tokens += tokens_per_name
    num_tokens += 3
    return num_tokens