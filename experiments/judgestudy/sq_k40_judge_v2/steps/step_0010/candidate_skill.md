# Question Answering Skill

## Core Analytical Strategies
- **Keyword & Clue Anchoring**: Scan the question for distinctive markers (dates, names, numbers, unique phrases) and Jeopardy-style descriptors. Use these as anchors to quickly locate the relevant `[DOC]` passages.
- **Reference Resolution**: When questions contain demonstratives or possessives (e.g., "this country", "its"), explicitly identify the exact entity they refer to in the context before formulating the answer.
- **Multi-Document Cross-Verification**: If multiple passages address the question, scan all relevant documents to confirm facts and resolve ambiguities. Prefer the most direct or consistently stated match.

## Answer Extraction Rules
- **Strict Conciseness**: Output only the exact entity, word, or short phrase requested. Never include full sentences, explanations, or conversational filler inside `<answer>...</answer>`.

- **Semantic Slot & Distractor Filtering**: Parse the question to identify the precise semantic role requested (e.g., person, location, business type). Strictly filter candidates to match that role. Explicitly verify that the candidate entity actually satisfies the question's primary descriptor, discarding loosely matching items, tangential examples, or literal string matches that point to the wrong subject.
- **Cloze & Jeopardy Parsing**: Treat declarative statements, Jeopardy-style clues, and trailing blanks as direct fill-in-the-blank requests. Extract the exact missing subject or entity, never a category, boolean, or descriptive phrase. Be alert for puns, wordplay, or double meanings; map descriptors directly to the core noun or proper name that fulfills the clue's intent.
- **Exact Term Preference**: Prioritize the exact term found in the context over synonyms, acronyms, or full names. If the context uses "C", answer "C". If it uses "Genet", answer "Genet". Only expand if explicitly asked.
- **Zero Reasoning in Tags**: Perform all analysis and step-by-step thinking before the `<answer>` tag. The content inside the tags must be the final answer only.

## Execution Workflow
1. Read the question and highlight key identifiers or descriptive clues.
2. Search the context for those identifiers or their immediate synonyms. Ignore irrelevant tangential documents.
3. Perform a single-sentence verification linking the question's core descriptor directly to the extracted entity, confirming exact textual alignment and grammatical slot satisfaction. Skip extended analysis for straightforward trivia matches and explicitly rule out incidental or tangential matches.
4. Output only the core answer inside `<answer>...</answer>` tags.

- **Slot & Constraint Alignment**: Parse implicit question slots and explicit constraints (e.g., 'this holiday', 'First name of...', 'of it'). Extract only the term that directly fills the requested slot, strictly mirroring the grammatical form, number, and length demanded. Do not expand to full names, titles, or compound phrases unless explicitly required.
