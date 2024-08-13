def LMU_list_models(speedtest=False):
    import ollama
    import requests
    import dotenv
    import os
    import tenacity

    dotenv.load_dotenv(".env")
    dotenv.load_dotenv("./se_gym/.env")
    dotenv.load_dotenv("./../se_gym/.env")
    assert os.getenv("API_USERNAME") is not None
    assert os.getenv("API_PASSWORD") is not None
    client = ollama.Client(
        host="https://ollama.mobile.ifi.lmu.de/api/",
        auth=requests.auth.HTTPBasicAuth(os.getenv("API_USERNAME"), os.getenv("API_PASSWORD")),
    )
    models = client.list()
    models = sorted(models["models"], key=lambda x: x["size"])
    pop = ["modified_at", "model", "digest", "details", "parameter_size", "quantization_level"]
    for m in models:
        for p in pop:
            m.pop(p, None)

    if speedtest:

        @tenacity.retry(stop=tenacity.stop_after_delay(10))
        def test(model):
            res = client.chat(
                model=model,
                messages=[
                    dict(
                        role="user",
                        content="What are the first 5 sentences of the declaration of independence?",
                    )
                ],
                options=dict(num_predict=100),
            )
            if isinstance(res, Exception):
                return -1
            else:
                return res["eval_count"] / res["eval_duration"] * 10**9

        def get_speed(model, n=3):
            best = -1
            for _ in range(n):
                try:
                    speed = test(model)
                    print(f"Speed of {model}: {speed} tokens/s")
                    if speed > best:
                        best = speed
                except Exception:
                    pass
            return best

        for model in models:
            model["speed"] = get_speed(model["name"], 3)

    return models


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="List all models available in the Ollama API")
    parser.add_argument(
        "--speedtest",
        help="Run a speed test on the models",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()
    models = LMU_list_models(speedtest=args.speedtest)
    for model in models:
        print(model)
