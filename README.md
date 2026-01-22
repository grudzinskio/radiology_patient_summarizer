# Hack 4 Health Hackathon
Thank you for participating in the Hack 4 Health competition!
In collaboriation with MSOE and the Medical College of Wisconsin, AI-Club is hoping to provide an opportunity for our talented students to gain more hands-on AI experience for the chance to compete in a $6000, 3-day hackathon -- as well as build solutions that ultimately will feed into MSOE's Data Science Practicum, then into MCW itself!

For more information about what an appropriate solution looks like, as well as important dates, please refer to the [Hack 4 Health Rubric](https://msoe365-my.sharepoint.com/:w:/g/personal/storoeb_msoe_edu/IQDnsSnjQao-Q4V6Ktbm2o58AX4-nZzgCxJ5jy45kSz11RY?e=HBD8UV)

*Note*: Before you pull the repo, perform `git lfs install` to ensure you pull the large CSV. If it does not properly pull or you forgot to install, perform `git lfs pull`

# LLM API Keys
There are multiple options to running Large Language Models (LLMs) on or off of Rosie. First is using the LLM on Rosie's own H100.

## Gemini API keys (free tier)

You can also make a free Gemini account via [Google AI Studio](https://aistudio.google.com/) and get a rate-limited free tier of Gemini API keys.

There is a tutorial on Google AI Studio's Page regarding setup, but please reach out to Brett Storoe (`storoeb@msoe.edu`) or Adam Haile (`hailea@msoe.edu`) with any questions.

## Llama model is running on Rosie

Since so many of you are using this for the hackathon, the Gemini option above may be better (more consistent availability / less contention).

First, install the OpenAI Python package:

```bash
pip install openai
```

Then, use the following code to interact with the Llama model:

```python
from openai import OpenAI

stream = True

client = OpenAI(
    base_url='http://dh-dgxh100-2.hpc.msoe.edu:8000/v1',
    api_key="not_used"  # this field needs to be included but is ignored
)

chat_completion = client.chat.completions.create(
    model="meta/llama-3.3-70b-instruct",
    messages=[{"role": "user", "content": "Why is MSOE the best school to study CS and AI?"}],
    stream=stream
)

if stream:
    for event in chat_completion:
        if event.choices[0].finish_reason:
            print(event.choices[0].finish_reason,
                  event.usage['prompt_tokens'],
                  event.usage['completion_tokens'])
        else:
            print(event.choices[0].delta.content, sep='', end='')
else:
    print(chat_completion.choices[0].message.content)
```

## OpenAI API keys (reimbursable)

Groups that are having difficulty using the free tiers on Rosie or with Gemini can spend up to **$10** on OpenAI API keys; this will be reimbursed by AI Club. Please have a **single, documented API key** that will be used for this hackathon.

After the hackathon, reach out to Brett Storoe (`storoeb@msoe.edu`) for reimbursement.