# Question Answering Skill

## Core Analytical Strategies
- **Keyword & Clue Anchoring**: Scan the question for distinctive markers (dates, names, numbers, unique phrases) and Jeopardy-style descriptors. Use these as anchors to quickly locate the relevant `[DOC]` passages.

- **Snippet & Title Leverage**: For trivia and factual queries, scan document titles (`[TLE]`) and opening snippets first. These often contain the exact answer or direct paraphrase, allowing rapid extraction before reading full paragraphs.
- **Reference Resolution**: When questions contain demonstratives or possessives (e.g., "this country", "its"), explicitly identify the exact entity they refer to in the context before formulating the answer.
- **Multi-Document Cross-Verification**: If multiple passages address the question, scan all relevant documents to confirm facts and resolve ambiguities. Prefer the most direct or consistently stated match.

## Answer Extraction Rules
- **Strict Conciseness**: Output only the exact entity, word, or short phrase requested. Never include full sentences, explanations, or conversational filler inside `<answer>...</answer>`.
- **Trivia/Fragment Handling**: Treat incomplete sentences, Jeopardy-style clues, cloze blanks, and declarative statements as direct fill-in-the-blank requests. Map descriptive attributes directly to the exact subject entity in the context, ignoring conversational framing, trailing punctuation, or metadata.
- **Exact Term Preference**: Prioritize the exact term found in the context over synonyms, acronyms, or full names. If the context uses "C", answer "C". If it uses "Genet", answer "Genet". Only expand if explicitly asked.
- **Zero Reasoning in Tags**: Perform all analysis and step-by-step thinking before the `<answer>` tag. The content inside the tags must be the final answer only.

## Execution Workflow
1. Read the question and highlight key identifiers or descriptive clues.
2. Search the context for those identifiers or their immediate synonyms. Ignore irrelevant tangential documents.
3. Perform a single-sentence verification trace linking the question's core descriptor to the extracted entity. Skip extended analysis for straightforward trivia queries to maintain conciseness.
4. Output only the core answer inside `<answer>...</answer>` tags.

- **Proper Noun Pruning**: Strip non-essential descriptive suffixes or generic descriptors (e.g., 'Jr.', 'Sr.', 'Desert', 'River', 'Base') unless they are strictly part of the official title or explicitly requested. Default to the shortest, most direct entity name found in the context (e.g., 'Sahara' over 'Sahara Desert', 'Shepard' over 'Alan B. Shepard, Jr.') to avoid over-specification.
- **Constraint-Driven Selection**: When multiple entities partially match a query, filter strictly by the most restrictive clue (e.g., exact dates, unique actions, or implicit references like 'seen here'). Discard prominent but loosely matching items. Prioritize the entity that uniquely satisfies all constraints simultaneously.
