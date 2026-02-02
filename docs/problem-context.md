# Hack 4 Health Problem Statement

Radiology reports are a central component of modern medical diagnosis. However, they are primarily written for other clinicians—not patients. As a result, these reports contain dense terminology, modality-specific jargon, abbreviations, and interpretive phrasing that can be difficult or impossible for most patients to understand.

Improving patient comprehension of radiological findings is a major national priority, aligned with movements toward shared decision-making, transparency in care, and improved health literacy. Recent advances in generative AI offer promising tools to translate complex clinical information into accessible, patient-friendly summaries. However, these systems introduce new risks, including hallucination, over-simplification, omission of critical findings, and unintended clinical advice.

This hackathon challenges participants to design and evaluate AI-driven systems that both generate accurate patient-friendly summaries and rigorously validate the safety and correctness of those summaries. While the long-term application domain is radiology, the hackathon itself will use a curated public dataset consisting of biomedical sentences, paragraphs, and abstracts paired with expert-authored lay summaries. This approach ensures compliance with IRB and data-use requirements while still enabling teams to address the core technical, ethical, and communication challenges of medical text simplification with a primary emphasis on validation, error detection, and trustworthiness.

The "Hack 4 Health" Hackathon builds on MSOE's commitment to experiential learning, responsible AI, and community impact through data-driven innovation.

Top-performing hackathon solutions will be selected for further development in the Spring 2026 CSC4801 Data Science Practicum, where student teams will refine, expand, and operationalize the prototypes using domain-specific clinical data in collaboration with faculty and clinical partners.

## Key Considerations for Your Solution

- **Accuracy & Fidelity**: No invented findings; preserve entities, measurements, and uncertainty.
- **Safety**: Avoid medical advice, false reassurance, or alarmist tone.
- **Readability & Accessibility**: Target a welcoming reading level; empathetic tone; language options are an additional plus.
- **Explainability**: Provide confidence cues or provenance (e.g., which source lines support which summary statements).
- **Human-in-the-Loop**: Summaries should be easy for subject-matter experts to review, approve, and improve.
- **Sourcing & Standards**: Teams must source and justify terminology glossaries, readability frameworks, and patient-communication guidelines.
- **Novel vs. Known Approaches**: Both have distinct advantages and drawbacks. Teams must clearly demonstrate their chosen approach's effectiveness and benefits relative to the alternative.
- **Scalability**: Consider cost, performance, and integration into real-world clinical workflows.

## Beyond "Just a Chatbot"

We assume your team can build a functioning chatbot interface. Generative AI can do that in moments. What we are evaluating is how well we can trust your system in a medical context.

Your presentation should focus on what design choices, safeguards, and domain-specific adaptations set your approach apart for biomedical and patient-facing communication? How does your work build on or improve prior approaches, and what validation, monitoring, and feedback pipelines have you put in place to demonstrate safety, reliability, and real-world readiness?

## Project Details

### Your Team

While not required, we encourage you to work with a team!

- **Member Count**: 1–8 people per group
- **Sign-up Deadline**: There is no deadline for sign-ups. As long as you present on January 25th, your solution will be considered.

### The Solution / Data

Refer to "The Problem Statement" above for what the judges will look for. The final decision will be based solely on what you share during the presentation—the judges will not be reviewing code repositories. This repository contains base data to get started:

- **Merged Datasets**: Multiple biomedical-focused datasets combined together.
- **Data Descriptions**: Description of each combined dataset and their contents.
- **LLM APIs**: See [Hackathon Instructions](hackathon-instructions.md) for setup.

### The Presentation

Presentations are limited to **5 minutes** per team (strictly enforced).

- Explain how your solution works to non-technical audiences.
- Include design choices, safeguards, and domain-specific adaptations; validation and monitoring pipelines; safety and real-world readiness.
- **Live Demo**: Optional, and should not exceed 2 minutes of the presentation.
