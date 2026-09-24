# Question Answering Skill

## Trivia & Clue-Based Extraction Rules
- **Declarative Clue Handling**: Treat complete sentences or statements as direct queries for a missing entity. Do not answer with "True/False" or descriptions; extract the specific noun/title referenced.
- **Canonical Shortest Form**: Default to the shortest, most widely recognized identifier for an entity. Omit titles, honorifics, full middle names, and descriptive clauses (e.g., output "Boss" not "Boss Tweed"; "Napoleon" not "Napoleon Bonaparte").
- **Compound Name Integrity**: Do not truncate compound or multi-word proper nouns. Preserve essential connectors and modifiers (e.g., output "Funk & Wagnalls", not "Funk"; "Forbes magazine", not "Forbes").
- **Exact String Matching**: Output the precise word or short phrase requested. Preserve exact capitalization, singular/plural form, and avoid adding filler words unless they are part of the canonical name.
- **Constraint Over Prominence**: When multiple entities in the context could fit a vague clue, select the one that strictly satisfies the unique constraint in the question. If the clue specifies a particular identifier (e.g., surname, specific campus), default to that exact form rather than the most prominent or modern equivalent.
- **Target Concept Isolation**: For fragmented, definition-style, or Jeopardy prompts, isolate the single target concept being queried. Ignore adjacent metadata, dates, or descriptive phrases in the context.
- **Avoid Role/Description Outputs**: Never output a person's title, role, or a film/book's genre/director summary. Extract only the named entity itself (e.g., output "Brunei" for a sultan query; output "Romeo and Juliet" for a West Side Story reference).
- **Exact Granularity Matching**: Match the precise scope requested. If the clue specifies a sub-category or specific variant, output that exact term rather than the broader class or a general descriptor.
- **Minimal Reasoning**: Provide only a single sentence linking the clue to the extracted entity before the final answer. Keep `<answer>` tags strictly for the exact target string.
