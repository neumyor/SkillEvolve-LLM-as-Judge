# Question Answering Skill

## Context Navigation & Inference
- **Leverage Structural Tags**: Use `[DOC]`, `[TLE]`, and `[PAR]` markers to segment and scan the context efficiently.
- **Resolve Nicknames & Slogans**: When questions contain colloquial phrases, brand names, or slogans, search across multiple documents for explicit mappings or parenthetical clarifications that link the phrase to a concrete entity.

- **Map Colloquial & Pop-Culture Pointers**: Clues often reference TV plots, song lyrics, slogans, or literary metaphors (e.g., 'lathering up in Pam's shower', 'I Like Ike'). Map these figurative pointers directly to their canonical named entities in the context. Discard the literal phrasing of the pointer and output only the exact entity name.

## Core Answering Principles
- **Handling Jeopardy-Style Clues & Trivia Statements**: Questions often appear as incomplete sentences or factual statements. Parse the clue to isolate the **missing entity slot** and its **descriptive constraints** (e.g., 'this warlike city-state', 'this peachy state'). Treat the question as a fill-in-the-blank or identification task. Never interpret statement-based clues as True/False. Scan the context to find the entity that satisfies all constraints, prioritizing exact matches over assumptions.
- **Demonstrative & Possessive Resolution**: Questions frequently use vague references like "this settlement" or "his discovery". Scan the context to find the specific entity that satisfies the description. Prioritize explicit matches over assumptions.

- **Compound Descriptor Convergence**: Clues often use comma-separated or hyphenated noun phrases (e.g., 'Georgia guy, flag-fashioning pop painter') to point to an answer. Parse each segment as an independent constraint. The correct entity must satisfy all segments simultaneously. Discard literal interpretations of individual segments if they conflict, focusing on the convergent entity.
- **Title-First & Proximity Scanning**: Prioritize checking `[TLE]` markers and the opening lines of `[PAR]` blocks. Trivia contexts frequently embed the answer directly in titles or co-occur within a few words of the question's key constraints. Scan these high-signal zones first before parsing deeper paragraphs.
- **Multi-Passage Corroboration**: When the context contains multiple documents, cross-reference them to confirm the answer. Convergence across passages increases confidence.

- **Handle Fragments, Ellipses & Appositives**: Questions often contain trailing ellipses (`...`), cut-off syntax, or standalone noun phrases/titles. Ignore non-semantic noise and focus on core identifying constraints. Additionally, treat descriptive phrases or appositives (e.g., 'this South American capital') as primary search anchors to locate candidate entities.

- **Category & Hypernym Resolution**: Questions frequently use collective or generic pointers (e.g., 'these birds', 'this material', 'lively dance') to target a class or type rather than a specific instance. Scan the context for the explicit hypernym or category label that satisfies the description, and extract that exact term as the answer.

- **Definition & Equivalence Resolution**: When clues function as definitions, synonyms, or colloquial labels (e.g., 'A short, witty saying', 'Americans refer to Emmentaler as this'), scan for explicit dictionary-style definitions, glossary entries, or 'X is known as/called Y' structures. Map the clue's descriptive phrase directly to the canonical term defined in the text.

## Answer Formatting & Output
- **Enclose Answers**: Always place the final answer inside `<answer>...</answer>` tags.
- **Canonical Short-Name Priority**: Always extract the shortest, most recognizable identifier for the entity. Aggressively strip descriptive suffixes, generic qualifiers, and full formal names (e.g., output 'Sirius' not 'Sirius Satellite Radio', 'Roanoke' not 'Roanoke Island', 'George Bush' not 'George H. W. Bush'). If the clue points to a common name or brand, use that exact short form. Never output definitions, descriptions, or multi-word explanatory phrases.
- **Morphological & Plurality Alignment**: Match the grammatical number and word form (noun vs. adjective vs. verb) of the expected answer. If the context uses a different form (e.g., singular vs. plural, base verb vs. gerund), normalize to the standard dictionary form or the form implied by the clue's syntax. Prioritize the head term over compound phrases.
- **Mandatory Explicit Grounding**: Always precede the final answer with a single-sentence reasoning step that explicitly quotes or closely paraphrases the exact context span containing the answer. Do not rely on external knowledge or implicit assumptions; the evidence must be directly visible in the provided text.

- **Explicit Constraint Mapping**: In the reasoning step, explicitly state how the found evidence satisfies each constraint from the question (e.g., 'The text confirms X is Y, matching the clue about Z'). This forces alignment between the query's requirements and the extracted span.

- **Resolve Placeholders & Figurative Terms**: Questions frequently use placeholders ('this [entity]', '& this [entity]'), quoted metaphors/puns, or standalone noun phrases to point to the answer. Treat these as direct identifiers and map them to the specific named entity in the context, ignoring the literal phrasing of the pointer itself.

- **Pronoun & Predicate-First Parsing**: Questions frequently begin with possessive pronouns ('Its...', 'His...') or definite articles ('The...') followed by a property or action, omitting the subject. Treat these openings as defining attributes rather than grammatical subjects. Scan the context to find the entity that logically serves as the subject satisfying the subsequent predicate.

- **Noise Filtering via Cross-Doc Repetition**: Search contexts often contain noisy, fragmented, or boilerplate snippets. Prioritize candidate answers that are explicitly repeated or corroborated across multiple independent `[DOC]` blocks. Disregard isolated mentions or metadata-heavy titles that lack semantic confirmation in the paragraph text.
