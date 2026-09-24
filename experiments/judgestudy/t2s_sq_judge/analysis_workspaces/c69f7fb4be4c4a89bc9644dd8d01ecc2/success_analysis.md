# Success Memory Item 1
## Title
Parse Possessive and Location Modifiers in Trivia Prompts
## Description
When a question uses phrases like "this city's [Team]" or similar possessive/location cues, treat them as direct pointers to extract a specific geographic or categorical attribute.
## Content
Identify the target entity type requested by the modifier. Scan the context for the named subject paired with the modifier. Extract only the corresponding attribute (e.g., city name) linked to that subject, ignoring surrounding narrative or unrelated facts.

# Success Memory Item 2
## Title
Isolate Core Entities from Noisy Contextual Data
## Description
Retrieved documents often contain extraneous details like pricing, dates, or secondary topics. Focus strictly on the sentence or phrase containing the target entity and its direct descriptor.
## Content
Locate the exact team or subject name in the context. Extract the immediately associated value (e.g., city, year, player) without incorporating adjacent clauses about facilities, finances, or historical records unless they redefine the primary relationship.

# Success Memory Item 3
## Title
Enforce Minimalist Output for Fill-in-the-Blank Queries
## Description
Trivia and Jeopardy-style questions require precise, single-value responses. Avoid generating explanatory sentences or listing multiple candidates.
## Content
After identifying the correct attribute, strip away all contextual framing. Output only the isolated value inside the specified tags. This ensures compliance with automated evaluation metrics that expect exact string matches.
