# Success Memory Item 1
## Title
Clue-to-Context Alignment
## Description
Extract specific named entities and relational descriptors from the prompt and systematically map them to overlapping details in the retrieved documents to isolate the target answer.
## Content
When processing trivia or identification queries, break the prompt into core components (e.g., person, setting, relationship, role). Cross-reference each component against the retrieved snippets to find the document that satisfies the maximum number of constraints simultaneously. This multi-factor matching reduces ambiguity and confirms the exact entity before finalizing the response.

# Success Memory Item 2
## Title
Contextual Primacy Over Prompt Phrasing
## Description
Prioritize explicit factual matches from the provided context over loose or potentially misleading temporal/descriptive language in the original prompt.
## Content
Prompts may use relative terms like "recent," "classic," or "modern" that do not strictly align with publication dates. If the retrieved context contains a perfect match for all other identifying clues, accept the contextual result regardless of the prompt's temporal framing. Trivia language often relies on relative perspective; let the evidence dictate the answer rather than external assumptions.

# Success Memory Item 3
## Title
Tag-Isolated Answer Extraction
## Description
Place only the concise final value inside the designated XML tags, completely excluding reasoning, alternatives, or conversational filler.
## Content
After determining the correct answer, strip away all explanatory text, synonyms, or secondary options. Enclose solely the definitive answer string within the required `<answer>...</answer>` tags. This ensures clean parsing, prevents metric penalties from extra characters, and strictly adheres to automated evaluation formats.
