# Question Answering Skill

## Context Navigation & Inference
- **Leverage Structural Tags**: Use `[DOC]`, `[TLE]`, and `[PAR]` markers to segment and scan the context efficiently.
- **Resolve Nicknames & Slogans**: When questions contain colloquial phrases, brand names, or slogans, search across multiple documents for explicit mappings or parenthetical clarifications that link the phrase to a concrete entity.

## Core Answering Principles
- **Handling Jeopardy-Style Clues & Trivia Statements**: Questions may appear as incomplete sentences or factual statements rather than direct interrogatives. Treat these as fill-in-the-blank or identification queries. Never interpret statement-based clues as True/False questions; always identify the missing entity or term. When context contains multiple related terms, select the one that precisely completes the clue or matches the specific trivia fact, avoiding broad generalizations.
- **Demonstrative & Possessive Resolution**: Questions frequently use vague references like "this settlement" or "his discovery". Scan the context to find the specific entity that satisfies the description. Prioritize explicit matches over assumptions.
- **Keyword Spotting & Mapping**: Quickly scan document titles and paragraphs for exact keywords, dates, and unique proper nouns from the question to locate the answer span efficiently.
- **Multi-Passage Corroboration**: When the context contains multiple documents, cross-reference them to confirm the answer. Convergence across passages increases confidence.

## Answer Formatting & Output
- **Enclose Answers**: Always place the final answer inside `<answer>...</answer>` tags.
- **Be Strictly Concise**: Provide only the direct answer. Do not repeat the question or include reasoning/explanations inside the tags. Match the exact expected term. Prefer last names over full names (e.g., "Genet" not "Jean Genet"), single letters/abbreviations if implied (e.g., "C" not "Vitamin C"), and bare entities without descriptive labels (e.g., "U2" not "U2 tribute band").
- **Optional Justification**: Precede the final tag with a single-sentence reasoning step linking the question constraints to the found evidence, if helpful.
