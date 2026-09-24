# Question Answering Skill

## Core Analytical Strategies
- **Keyword & Clue Anchoring**: Scan the question for distinctive markers (dates, names, numbers, unique phrases) and Jeopardy-style descriptors. Use these as anchors to quickly locate the relevant `[DOC]` passages.
- **Reference Resolution**: When questions contain demonstratives or possessives (e.g., "this country", "its"), explicitly identify the exact entity they refer to in the context before formulating the answer.

- **Clue & Fragment Parsing**: For Jeopardy-style clues, name pairs, or declarative statements, isolate the single core entity, location, or concept being queried. Do not infer relationships, repeat parts of the question, or output descriptive phrases. Anchor strictly to the definitive factual noun or proper name.

- **Primary Subject Isolation**: When contexts mention multiple related entities or tangential examples, isolate the single entity that directly satisfies the question's core descriptor. Discard loosely matching items, historical anecdotes, or secondary mentions to prevent over-specification.
- **Multi-Document Cross-Verification**: If multiple passages address the question, scan all relevant documents to confirm facts and resolve ambiguities. Prefer the most direct or consistently stated match.

## Answer Extraction Rules
- **Strict Conciseness**: Output only the exact entity, word, or short phrase requested. Never include full sentences, explanations, or conversational filler inside `<answer>...</answer>`.
- **Trivia/Fragment Handling**: Treat incomplete sentences or clue-like questions as direct requests for a missing keyword. Identify the target entity immediately without describing relationships or generating categories.
- **Exact Term & Variant Alignment**: When multiple variants of an entity exist in the context (e.g., full vs. short names, formal vs. nicknames, expanded vs. abbreviated), strictly default to the shortest, most direct identifier that matches the question's implied length. For company, organization, or location names, strip generic descriptive suffixes (e.g., 'Cards', 'Inc.', 'Company', 'Group', 'Foundation', 'Mountains', 'of Venus') unless explicitly required by the question or integral to the official short name. Strip non-essential middle names, initials, and geographic/event suffixes. Prefer the most commonly used or context-primary variant over obscure alternatives.
- **Zero Reasoning in Tags**: Perform all analysis and step-by-step thinking before the `<answer>` tag. The content inside the tags must be the final answer only.

## Execution Workflow
1. Read the question and highlight key identifiers or descriptive clues.
2. Search the context for those identifiers or their immediate synonyms. Ignore irrelevant tangential documents.
3. Perform a rapid, single-sentence verification linking the question's core descriptor to the extracted entity, confirming exact textual alignment and grammatical slot satisfaction. Skip extended analysis for straightforward matches to maintain speed.
4. Output only the core answer inside `<answer>...</answer>` tags.
