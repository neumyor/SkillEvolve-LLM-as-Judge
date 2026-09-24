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

## Answer Formatting & Output
- **Enclose Answers**: Always place the final answer inside `<answer>...</answer>` tags.
- **Be Strictly Concise**: Provide only the direct answer. Do not repeat the question or include reasoning/explanations inside the tags. Match the exact expected term. Prefer last names over full names (e.g., "Genet" not "Jean Genet"), single letters/abbreviations if implied (e.g., "C" not "Vitamin C"), and bare entities without descriptive labels (e.g., "U2" not "U2 tribute band").

- **Granularity-First Extraction**: Prioritize the exact phrase length and structure implied by the clue. Strip non-essential geographic, proper-noun, or descriptive modifiers when the clue targets a base category (e.g., output 'eagle' not 'White Eagle', 'falcon' not 'Maltese Falcon'). Normalize articles and plurality to match the question's syntax (e.g., 'Fungi' not 'Fungus', 'a balloon' not 'Speech balloon'). Select the single most direct term; avoid listing multiple synonyms or alternatives found in the text. Only retain modifiers if strictly required to satisfy the clue's constraints.
- **Optional Justification**: Precede the final tag with a single-sentence reasoning step linking the question constraints to the found evidence, if helpful.

- **Explicit Constraint Mapping**: In the reasoning step, explicitly state how the found evidence satisfies each constraint from the question (e.g., 'The text confirms X is Y, matching the clue about Z'). This forces alignment between the query's requirements and the extracted span.

- **Resolve Placeholders & Figurative Terms**: Questions frequently use placeholders ('this [entity]', '& this [entity]'), quoted metaphors/puns, or standalone noun phrases to point to the answer. Treat these as direct identifiers and map them to the specific named entity in the context, ignoring the literal phrasing of the pointer itself.

- **Pronoun & Predicate-First Parsing**: Questions frequently begin with possessive pronouns ('Its...', 'His...') or definite articles ('The...') followed by a property or action, omitting the subject. Treat these openings as defining attributes rather than grammatical subjects. Scan the context to find the entity that logically serves as the subject satisfying the subsequent predicate.
