# Success Memory Item 1
## Title
Leverage Verbatim Context Anchors
## Description
Treat exact or near-exact phrasing matches between the prompt and retrieved documents as direct pointers to the target entity.
## Content
When a question contains distinctive phrasing that appears directly within the context, use that passage as the primary identification signal. Extract the named subject from the matching sentence, then examine adjacent text for corroborating details to ensure the match aligns with the full scope of the query before proceeding.

# Success Memory Item 2
## Title
Attribute-to-Snippet Mapping
## Description
Decompose multi-clue prompts into discrete factual requirements and systematically map each to specific context passages.
## Content
Break down complex trivia questions into individual constraints (e.g., geographic role, professional title, temporal event). Search the retrieved context to locate explicit evidence for each constraint across different documents. Synthesize the final answer only after confirming that all mapped attributes consistently point to a single entity.

# Success Memory Item 3
## Title
Cross-Source Triangulation
## Description
Confirm identified candidates using independent context snippets rather than relying on isolated matches.
## Content
After locating a potential subject through initial clues, consult separate context passages (such as biographical summaries, archival reports, or official records) to independently confirm key claims. Mutual agreement across diverse sources strengthens confidence and prevents misidentification caused by fragmented or ambiguous snippets.
