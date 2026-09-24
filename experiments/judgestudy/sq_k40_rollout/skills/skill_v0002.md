# Question Answering Skill

## Context Navigation & Inference
- **Leverage Structural Tags**: Use `[DOC]`, `[TLE]`, and `[PAR]` markers to segment and scan the context efficiently.
- **Resolve Nicknames & Slogans**: When questions contain colloquial phrases, brand names, or slogans, search across multiple documents for explicit mappings or parenthetical clarifications that link the phrase to a concrete entity.

## Core Answering Principles
- **Handling Jeopardy-Style Clues & Trivia Statements**: Questions often appear as incomplete sentences or factual statements. Parse the clue to isolate the **missing entity slot** and its **descriptive constraints** (e.g., 'this warlike city-state', 'this peachy state'). Treat the question as a fill-in-the-blank or identification task. Never interpret statement-based clues as True/False. Scan the context to find the entity that satisfies all constraints, prioritizing exact matches over assumptions.
- **Demonstrative & Possessive Resolution**: Questions frequently use vague references like "this settlement" or "his discovery". Scan the context to find the specific entity that satisfies the description. Prioritize explicit matches over assumptions.
- **Keyword Spotting & Mapping**: Quickly scan document titles and paragraphs for exact keywords, dates, and unique proper nouns from the question to locate the answer span efficiently.
- **Multi-Passage Corroboration**: When the context contains multiple documents, cross-reference them to confirm the answer. Convergence across passages increases confidence.

- **Handle Fragments, Ellipses & Appositives**: Questions often contain trailing ellipses (`...`), cut-off syntax, or standalone noun phrases/titles. Ignore non-semantic noise and focus on core identifying constraints. Additionally, treat descriptive phrases or appositives (e.g., 'this South American capital') as primary search anchors to locate candidate entities.

## Answer Formatting & Output
- **Enclose Answers**: Always place the final answer inside `<answer>...</answer>` tags.
- **Be Strictly Concise**: Provide only the direct answer. Do not repeat the question or include reasoning/explanations inside the tags. Match the exact expected term. Prefer last names over full names (e.g., "Genet" not "Jean Genet"), single letters/abbreviations if implied (e.g., "C" not "Vitamin C"), and bare entities without descriptive labels (e.g., "U2" not "U2 tribute band").

- **Verbatim Extraction Priority**: To prevent overly descriptive outputs, extract the target term exactly as it appears in the context. Do not paraphrase, expand, or add conversational qualifiers. Preserve original capitalization and formatting when possible to maximize exact-match probability.
- **Optional Justification**: Precede the final tag with a single-sentence reasoning step linking the question constraints to the found evidence, if helpful.

- **Resolve Placeholders & Figurative Terms**: Questions frequently use placeholders ('this [entity]', '& this [entity]'), quoted metaphors/puns, or standalone noun phrases to point to the answer. Treat these as direct identifiers and map them to the specific named entity in the context, ignoring the literal phrasing of the pointer itself.
