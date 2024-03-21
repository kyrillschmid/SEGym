from dotenv import load_dotenv
from openai import OpenAI

def call_model(system_prompt, user_prompt, model="gpt-4-0125-preview"):

    load_dotenv()
    client = OpenAI()

    #client = OpenAI(
    #    base_url = 'http://localhost:11434/v1',
    #    api_key='ollama', # required, but unused
    #)
    #model = "mistral"

    # Make the API call
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        response_format={ "type": "json_object" }
    )
    return response.choices[0].message.content