import requests
import json

API = 'http://localhost:8000/'


def login(api_key: str):
    res = requests.post(
        API + 'login', json={"api_key": api_key})
    if res.ok:
        return res.json()
    return None

def get_budgets(api_key: str):
    res = requests.get(
        API + 'budget', params={"api_key": api_key})
    if res.ok:
        return res.json()
    return None