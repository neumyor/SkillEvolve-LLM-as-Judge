# Failure Cause Item 1
## Title
Verbose Answer Span Extraction
## Description
The agent correctly identified the semantic link between the named characters and the show "Barney Miller" but failed to extract the minimal entity span required for an exact match.
## Content
The question "Inspector Luger,Wojo,Fish" is a trivia-style query asking for the source work containing these characters. The agent reasoned that they are "Characters in the TV series Barney Miller" and outputted that full phrase. However, the ground truth answer is simply the entity name "Barney Miller". The agent committed to a descriptive clause rather than the concise noun phrase, resulting in an Exact Match (EM) score of 0.0 despite high F1 overlap. This is a classic span-boundary error where the agent includes surrounding context words that are not part of the target entity.

# Failure Memory Item 1
## Title
Prioritize Minimal Entity Spans for Source Queries
## Description
When questions list entities and imply a request for their common source, the answer is typically the specific entity name itself, not a sentence describing the relationship.
## Content
In SearchQA and similar benchmarks, answers are usually short noun phrases or proper nouns. Agents should avoid generating full sentences or adding filler phrases like "Characters in..." or "From the show..." unless explicitly instructed. The goal is to extract the precise identifier (e.g., "Barney Miller") that satisfies the query, stripping away relational descriptors that do not contribute to the entity's identity.

# Failure Memory Item 2
## Title
Align Answer Granularity with Question Format
## Description:
Different question formats signal different expected answer lengths. List-based queries often seek a single unifying identifier.
## Content
When presented with a comma-separated list of proper nouns (e.g., character names, places), infer that the user seeks the unifying entity (the show, book, or location). Ensure the final answer is the name of that entity only. Do not confuse the *relationship* (they are characters) with the *answer* (the show title). Keep the output tight and focused on the core entity.

ACTION: TASK_COMPLETE
