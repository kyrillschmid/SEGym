import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("API_USERNAME")
PASSWORD = os.getenv("API_PASSWORD")

def make_api_request(method, url, data=None, json=True):
    """General purpose function to make API requests with Basic Authentication."""
    headers = {'Content-Type': 'application/json'} if json else {}
    response = requests.request(
        method=method,
        url=f"https://ollama.mobile.ifi.lmu.de/api{url}",
        headers=headers,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        json=data if json else None
    )
    return response.json() if response.status_code == 200 else response.text

def generate_completion(model, prompt, stream=False):
    data = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": stream
    }
    return make_api_request('POST', '/generate', data)

def make_chat_request(model, messages, stream=False):
    """Make a request to the chat completion endpoint."""
    url = "https://ollama.mobile.ifi.lmu.de/api/chat"
    data = {
        "model": model,
        "messages": messages,
        "stream": stream
    }
    response = requests.post(
        url=url,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        json=data,
        stream=stream
    )
    
    return response.json()

# Example usage
messages = [
    {"role": "user", "content": "Hello, how are you?"},
    {"role": "system", "content": "System initialized."},
]
