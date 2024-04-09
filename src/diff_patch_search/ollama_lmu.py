import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Credentials
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

# Example usage to fetch local models
#local_models = make_api_request('GET', '/tags')
#print(local_models)


def generate_completion(model, prompt, stream=False):
    data = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": stream
    }
    return make_api_request('POST', '/generate', data)

# Example call
#response = generate_completion("dolphin-mixtral:latest", "Why is the sky blue? Respond using JSON")
#print(response)

#generate_completion("dolphin-mixtral:latest", "Why is the sky blue?", stream=True)

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

#response = make_chat_request("gemma:latest", messages, stream=False)
#print(type(response))
#print(response)