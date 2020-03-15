import requests
import json

API = 'https://colykfinance.herokuapp.com/'


def login(api_key: str):
    res = requests.post(
        API + 'login', json={"api_key": api_key})
    if res.ok:
        return res.json()
    return None


def post_transaction(transaction: dict):
    res = requests.post(
        API + 'transaction', json=transaction)
    if res.ok:
        return res.json()
    return None


def get_budgets(api_key: str):
    res = requests.get(
        API + 'budget', params={"api_key": api_key})
    if res.ok:
        return res.json()
    return None


def get_categories(api_key: str):
    res = requests.get(
        API + 'category', params={"api_key": api_key})
    if res.ok:
        return res.json()
    return None
