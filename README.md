# Hack 4 Health Hackathon
Thank you for participating in the Hack 4 Health competition!
In collaboriation with MSOE and the Medical College of Wisconsin, AI-Club is hoping to provide an opportunity for our talented students to gain more hands-on AI experience for the chance to compete in a $6000, 3-day hackathon -- as well as build solutions that ultimately will feed into MSOE's Data Science Practicum, then into MCW itself!

For more information about what an appropriate solution looks like, as well as important dates, please refer to the [Hack 4 Health Rubric](https://msoe365-my.sharepoint.com/:w:/g/personal/storoeb_msoe_edu/IQDnsSnjQao-Q4V6Ktbm2o58AX4-nZzgCxJ5jy45kSz11RY?e=HBD8UV)

*Note*: Before you pull the repo, perform `git lfs install` to ensure you pull the large CVS. If it does not properly pull or you forgot to install, perform `git lfs pull`

# LLM API Keys
There are multiple options to running Large Language Models (LLMs) on or off of Rosie. First is using the LLM on Rosie's own H100.

## Gemini API keys (free tier)

You can also make a free Gemini account via [Google AI Studio](https://aistudio.google.com/) and get a rate-limited free tier of Gemini API keys.

Please reach out to Brett Storoe (`storoeb@msoe.edu`) or Adam Haile (`hailea@msoe.edu`) with any questions about setting this up.

## Llama 3.2 Multimodal (Vision) model is running on Rosie

Since so many of you are using this for the hackathon, the Gemini option above may be better (more consistent availability / less contention).

- **Endpoint**: `http://dh-dgxh100-2.hpc.msoe.edu:8001/v1/chat/completions`
- **Model**: `meta/llama-3.2-90b-vision-instruct`
- **Auth**: no API key required (send any bearer value; see examples)

### Python (Requests) — streaming response

```python
import base64
import json

import requests

invoke_url = "http://dh-dgxh100-2.hpc.msoe.edu:8001/v1/chat/completions"
stream = True

with open("roscoe.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

assert len(image_b64) < 180_000, "To upload larger images, use the assets API (see docs)"

headers = {
    "Authorization": "Bearer $NO_API_KEY_REQUIRED",
    "Accept": "text/event-stream" if stream else "application/json",
}

payload = {
    "model": "meta/llama-3.2-90b-vision-instruct",
    "messages": [
        {
            "role": "user",
            "content": f'What is in this image? <img src="data:image/png;base64,{image_b64}" />',
        }
    ],
    "max_tokens": 512,
    "temperature": 1.00,
    "top_p": 1.00,
    "stream": stream,
}

response = requests.post(invoke_url, headers=headers, json=payload)

if stream:
    complete_response = ""
    for line in response.iter_lines():
        if not line:
            continue
        try:
            resp = line.decode("utf-8")
            resp_json = json.loads(resp[5:])  # strips "data:"
            resp_str = resp_json["choices"][0]["delta"]["content"]
            complete_response += resp_str
        except Exception:
            pass
    print(complete_response)
else:
    print(response.json())
```

### Python (OpenAI-style SDK) — multimodal messages (data URL)

```python
import base64

from openai import OpenAI

with open("roscoe.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

client = OpenAI(
    base_url="http://dh-dgxh100-2.hpc.msoe.edu:8001/v1",
    api_key="not_used",
)

messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "What is in this image?"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
        ],
    }
]

completion = client.chat.completions.create(
    model="meta/llama-3.2-90b-vision-instruct",
    messages=messages,
    max_tokens=512,
    temperature=1.0,
    stream=False,
)

print(completion.choices[0].message.content)
```

## OpenAI API keys (reimbursable)

Groups that are having difficulty using the free tiers on Rosie or with Gemini can spend up to **$10** on OpenAI API keys; this will be reimbursed by AI Club. Please have a **single, documented API key** that will be used for this hackathon.

After the hackathon, reach out to Brett Storoe (`storoeb@msoe.edu`) for reimbursement.