[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340e965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/QTuIDktS)

# Hack 4 Health Hackathon Instructions

Thank you for participating in the Hack 4 Health competition! In collaboration with MSOE and the Medical College of Wisconsin, AI-Club is providing an opportunity for students to gain hands-on AI experience in a $6000, 3-day hackathon—and to build solutions that may feed into MSOE's Data Science Practicum and MCW.

For rubric, dates, and what judges look for, see the [Hack 4 Health Rubric](https://msoe365-my.sharepoint.com/:w:/g/personal/storoeb_msoe_edu/IQDnsSnjQao-Q4V6Ktbm2o58AX4-nZzgCxJ5jy45kSz11RY?e=HBD8UV).

**Note:** Before you pull the repo, run `git lfs install` so the large CSV is pulled. If it does not pull correctly, run `git lfs pull`.

---

## LLM API Keys

You have several options for running Large Language Models (LLMs).

### Gemini API keys (free tier)

Create a free Gemini account via [Google AI Studio](https://aistudio.google.com/) for a rate-limited free tier of Gemini API keys.

There is a tutorial on Google AI Studio's page for setup. Questions: Brett Storoe (`storoeb@msoe.edu`) or Adam Haile (`hailea@msoe.edu`).

### Llama on Rosie (MSOE HPC)

The Llama model runs on Rosie's H100. For high contention during the hackathon, the Gemini option above may be more reliable.

1. Install the OpenAI Python package:

   ```bash
   pip install openai
   ```

2. Use the following to call the Llama model (OpenAI-compatible API):

   ```python
   from openai import OpenAI

   stream = True

   client = OpenAI(
       base_url='http://dh-dgxh100-2.hpc.msoe.edu:8000/v1',
       api_key="not_used"  # required but ignored
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

### OpenAI API keys (reimbursable)

Teams that cannot use Rosie or Gemini can spend up to **$10** on OpenAI API keys; AI Club will reimburse. Use a **single, documented API key** for the hackathon.

After the hackathon, contact Brett Storoe (`storoeb@msoe.edu`) for reimbursement.
