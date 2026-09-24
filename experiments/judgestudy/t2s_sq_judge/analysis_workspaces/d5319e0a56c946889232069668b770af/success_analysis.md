# Success Memory Item 1
## Title
Landmark-to-Location Mapping
## Description
Directly associate specific named venues, events, or landmarks with their explicitly stated geographic location in the context to resolve place-based queries.
## Content
Extract the core subject from the prompt, locate its direct geographic pairing in the retrieved text, and use that location as the primary answer candidate.

# Success Memory Item 2
## Title
Contextual Distractor Isolation
## Description
Filter out alternative locations mentioned in the context by verifying which one uniquely satisfies the query's specific defining constraint.
## Content
When multiple cities or regions appear in the documents, cross-reference each against the prompt's key identifier (e.g., a specific holiday tradition or site) to discard irrelevant mentions and confirm the exact match.

# Success Memory Item 3
## Title
Strict Tag Encapsulation
## Description
Isolate the final extracted answer within the prescribed output markers, ensuring no extra text or formatting interferes with parsing.
## Content
Once the correct entity is confirmed, place only the precise answer string inside the required tags (e.g., `<answer>Value</answer>`), stripping all conversational filler or intermediate reasoning from the final output block.
