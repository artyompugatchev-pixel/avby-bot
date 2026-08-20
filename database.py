import json 
import os 
from config import SENT_FILE 
 
def load_sent_ids(): 
    if not os.path.exists(SENT_FILE): 
        return set() 
    try: 
        with open(SENT_FILE, 'r', encoding='utf-8') as f: 
            data = json.load(f) 
            return set(data) 
    except: 
        return set() 
 
def save_sent_id(ad_id, reset=False): 
    if reset: 
        with open(SENT_FILE, 'w', encoding='utf-8') as f: 
            json.dump([], f) 
        return 
    sent_ids = load_sent_ids() 
    sent_ids.add(ad_id) 
    with open(SENT_FILE, 'w', encoding='utf-8') as f: 
        json.dump(list(sent_ids), f) 
