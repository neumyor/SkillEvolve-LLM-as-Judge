# Success Memory Item 1
## Title
Direct Lyric-to-Entity Mapping
## Description
When answering queries containing specific quoted lyrics, prioritize exact phrase matching against retrieved text to directly associate the snippet with its corresponding title or creator.
## Content
Scan the context for verbatim matches of the provided lyrical lines. Once located, extract the immediately surrounding metadata (song title, artist, album) to form the initial answer candidate. This bypasses unnecessary inference when the context provides explicit lyrical attribution.

# Success Memory Item 2
## Title
Multi-Constraint Context Alignment
## Description
Confirm the identified entity by cross-referencing multiple independent details within the retrieved context to ensure all prompt constraints (e.g., release year, chart status) are satisfied.
## Content
After finding a lyrical match, examine additional context blocks for corroborating attributes like the release date, artist name, or awards. Only finalize the answer if the collected contextual signals consistently point to the same entity, reducing ambiguity and preventing mismatched results.

# Success Memory Item 3
## Title
Format-First Response Generation
## Description
Isolate the final answer and wrap it precisely in the requested delimiters, strictly omitting reasoning traces, explanations, or conversational filler to ensure structural compliance.
## Content
Review the prompt's output requirements before generation. Place only the concise, confirmed answer inside the specified tags (e.g., `<answer>...</answer>`). Maintain a clean, machine-readable output structure by separating the final result from any internal processing steps.
