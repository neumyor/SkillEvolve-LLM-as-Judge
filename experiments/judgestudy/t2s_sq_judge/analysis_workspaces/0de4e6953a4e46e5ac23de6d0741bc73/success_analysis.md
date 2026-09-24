# Success Memory Item 1
## Title
Constraint-Driven Entity Mapping
## Description
Translate explicit numerical, temporal, and geographic details from the prompt into direct search anchors within the retrieved context to isolate the target entity.
## Content
When a question contains specific parameters (e.g., duration, route, participant role), scan the context for exact or semantically equivalent matches of those parameters. Use the intersection of these constraints to filter out generic terms and pinpoint the precise named entity being requested.

# Success Memory Item 2
## Title
Cross-Snippet Consistency Check
## Description
Validate the candidate answer by confirming it aligns with the query constraints across multiple independent context passages.
## Content
Review several relevant snippets to ensure the identified entity consistently satisfies all stated conditions. If multiple documents independently corroborate the same entity under the given constraints, confidence in the selection increases and ambiguity is minimized.

# Success Memory Item 3
## Title
Strict Tag Encapsulation
## Description
Isolate the final derived answer within the designated XML tags, completely separating it from reasoning or supplementary text.
## Content
After synthesizing the correct entity, extract only the core value or name and place it strictly inside the required `<answer>...</answer>` tags. Omit explanations, qualifiers, or trailing punctuation within the tags to guarantee clean extraction by downstream evaluators or parsers.
