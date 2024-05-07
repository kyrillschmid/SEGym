from dotenv import load_dotenv
from openai import OpenAI
from groq import Groq
import os
from se_gym.ollama_lmu import make_chat_request


def call_model(system_prompt, user_prompt, api, model):
    load_dotenv()

    # LMU OLLAMA
    if api == "ollama_lmu":
        response = make_chat_request(
            model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        print("Response", response)
        return response["message"]["content"]

    # GROQ
    if api == "groq":
        client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    # OPENAI
    if api == "openai":
        client = OpenAI()

    # LOCAL OLLAMA
    if api == "ollama_local":
        client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    # Make the API call
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content
