# Success Memory Item 1
## Title
Extract and Map Core Query Entities
## Description
Isolate distinct proper nouns, relationships, and descriptive phrases from the prompt to create precise search anchors for scanning retrieved documents.
## Content
Break the question into key identifiers (e.g., character names, author, demographic details, setting). Use these terms to rapidly filter retrieved snippets, prioritizing passages where multiple identifiers co-occur to pinpoint the exact source containing the answer.

# Success Memory Item 2
## Title
Recognize Direct-Fact Trivia Patterns
## Description
Identify when a prompt is structured as a factual lookup or trivia clue, signaling that the context will contain an explicit statement linking the given attributes to the target answer.
## Content
When queries resemble quiz prompts or ask for a specific title/name tied to known entities, bypass complex inference. Locate the exact sentence or phrase that directly connects the provided attributes to the target entity and extract that connected term verbatim.

# Success Memory Item 3
## Title
Enforce Strict Tag Separation
## Description
Maintain a clean boundary between analytical reasoning and the required output format to guarantee constraint compliance.
## Content: Draft concise, step-by-step reasoning outside of designated answer markers. Place only the final extracted term or short phrase inside the specified tags, strictly avoiding question repetition, extra commentary, or formatting artifacts within the tag boundaries.
