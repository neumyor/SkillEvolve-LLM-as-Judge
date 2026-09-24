# Success Memory Item 1
## Title
Clue-Driven Context Alignment
## Description
Map specific narrative or structural clues from the prompt to their corresponding explicit statements in the retrieved text to isolate the target information.
## Content
When answering trivia or completion queries, identify unique identifiers in the question (e.g., character names, plot details, partial titles). Scan the context for sentences that combine these identifiers with the missing element. This direct alignment leverages the most relevant snippet and reduces reliance on inference.

# Success Memory Item 2
## Title
Verbatim Entity Extraction
## Description
Pull the exact missing term directly from declarative context sentences rather than paraphrasing or synthesizing across multiple sources.
## Content
Retrieved summaries frequently contain direct factual declarations (e.g., "named [Target]"). Prioritize extracting the precise string that completes the prompt's structure. Treat these explicit statements as the primary evidence, ignoring peripheral metadata like pricing, dates, or user reviews.

# Success Memory Item 3
## Title
Structured Output Enforcement
## Description
Apply the required formatting wrapper immediately after extraction and perform a rapid semantic substitution check before final submission.
## Content
Once the target string is isolated, wrap it in the designated tags without delay. Quickly substitute the answer back into the original question to verify grammatical flow and logical fit. This dual-step approach ensures strict compliance with output specifications while catching mismatched extractions early.
