import requests

URL = 'https://colykfinance.herokuapp.com/'

def login(api_key):
    res = requests.post(URL + 'login', {api_key:api_key})
    return res.json()