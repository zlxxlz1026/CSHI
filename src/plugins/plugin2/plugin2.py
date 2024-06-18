from src.plugins import *
import os
import json


@register(
    name="plugin2",
    enabled=True,
)
class Plugin2(Plugin):
    '''
    该插件根据user_id生成用户历史观看记录
    '''
    def __init__(self):
        super().__init__()
        self.conf = super().load_config()
        self.handlers["user_profile_init"] = self.generate_user_profile
    
    def check_user_profile(self, user_id: str) -> bool:
        folder_path = "./user_profile/"
        file_name = f"{user_id}.json"
        file_path = os.path.join(folder_path, file_name)
        
        if os.path.exists(file_path):
            return True
        else:
            return False
   
    def _map_gender_and_age(self, user_profile: dict) -> dict:
        if user_profile['gender'] == 'F':
            user_profile['gender'] = 'female'
        else:
            user_profile['gender'] = 'male'
        
        if user_profile['age'] == 1:
            user_profile['age'] = 'Under 18'
        
        return user_profile

            
    def generate_user_profile(self, message: Message):
        user_id = message.get("user_id")
        dataset_name = message.get("dataset")
        
        with open('./exp1_user_profile.jsonl', 'r', encoding='utf-8') as f:
            user_profiles = json.load(f)
        
        user_profile = user_profiles[str(user_id)]
        if not os.path.exists(f'./user_profile/{dataset_name}'):
            os.makedirs(f'./user_profile/{dataset_name}')
        with open(f'./user_profile/{dataset_name}/{user_id}.json', 'w', encoding='utf-8') as f:
            json.dump(user_profile, f, indent=4)