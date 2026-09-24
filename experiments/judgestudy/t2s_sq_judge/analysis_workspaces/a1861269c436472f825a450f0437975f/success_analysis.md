# Success Memory Item 1
## Title
Context-Gap Resolution via Candidate Filtering
## Description
When retrieved passages lack direct answers, extract all plausible entities from the context and use targeted prior knowledge to bridge the information gap.
## Content
Identify every person or organization mentioned in the snippets that aligns with the prompt's geographic or professional scope. Discard irrelevant matches, then apply verified domain knowledge to select the correct entity, treating the context as a candidate generator rather than a definitive source.

# Success Memory Item 2
## Title
Declarative Clue Decomposition
## Description
Convert fragmented or statement-style prompts into structured attribute queries to improve entity matching accuracy.
## Content
Isolate key constraints such as role, location, duration, and notable events from non-interrogative prompts. Map these attributes systematically to known public figures or historical records, enabling precise identification even when the prompt phrasing is unconventional.

# Success Memory Item 3
## Title
Unconditional Format Adherence
## Description
Preserve strict output templating rules throughout the reasoning process, regardless of intermediate uncertainty or missing evidence.
## Content
Decouple the final formatting step from the confidence level of the derivation. Always wrap the concluded answer in the required tags immediately upon resolution, ensuring structural compliance does not degrade due to complex or incomplete retrieval states.
