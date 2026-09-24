# Question Answering Skill

## Core Retrieval & Reasoning Principles
- **Clue & Entity Recognition**: Treat questions (especially trivia, Jeopardy-style, or incomplete prompts) as direct requests for a specific person, place, title, or concept. Parse the prompt to filter out introductory cues or "fluff" and isolate the core factual query.
- **Implicit Reference Resolution**: Map demonstratives like "this [noun]" directly to the concrete entity described in the context.
- **Direct Extraction & Context Scanning**: Systematically scan `[DOC]`, `[TLE]`, and `[PAR]` blocks for exact keyword matches. In noisy or repetitive contexts (e.g., scraped lists, flashcard dumps), ignore duplicated passages and isolate the single mention that directly defines or completes the query.
- **Constraint-Driven Verification**: Prioritize exact matches for numerical, temporal, or proper-noun constraints embedded in the clue. Discard candidates that satisfy the general topic but fail specific quantitative or categorical filters.

## Trivia & Clue Extraction Rules
- **Slot-Filling Strategy**: Treat Jeopardy-style and incomplete prompts as direct fill-in-the-blank requests. Identify the grammatical slot (subject, object, location) being queried and extract the exact term that fills it.
- **Clue Syntax Mapping**: Use structural cues like "this film", "it's the cry of", or "named for" to determine the expected answer type. Isolate the specific query target when multiple entities or conditions are present; do not return any entity merely mentioned in the prompt.
- **Canonical Phrasing & Modifier Stripping**: Preserve definite articles or standard modifiers only if they constitute the canonical trivia answer (e.g., "the atmosphere", "South Park"). Otherwise, strip non-essential adjectives, full biographical names, or contextual descriptors.
- **Noise Filtering**: In search-result-style or repetitive contexts, rapidly scan titles and snippets for exact keyword matches, then verify in the passage body before extracting. Ignore duplicated passages.
- **No Syntactic Mirroring**: Never repeat the prompt's phrasing, complete the sentence grammatically, or append contextual modifiers to the answer. Output only the isolated entity requested.
- **Gold Alignment**: Match the granularity and phrasing of the expected answer exactly. If the gold answer is a single word or short phrase, do not expand it into a full sentence or add explanatory clauses inside the answer tags.
- When multiple entities appear in the context, select the one that directly completes the clue or matches the expected brevity.
- Strip modifiers and use only surnames or key terms if the gold answer is minimal (e.g., output "C" not "Vitamin C", "Genet" not "Jean Genet").
- Do not guess based on metaphorical phrasing without verifying factual alignment.
- Avoid converting declarative clues into Yes/No answers.

## Answer Formatting Rules
- **Strict Tag Usage**: Always wrap the final answer in `<answer>...</answer>` tags.
- **Conciseness & Minimal Entities**: Prioritize exact, minimal entity extraction. The content inside tags must be the exact entity or a very short phrase. Preserve standard capitalization, omit leading articles unless integral, and avoid full sentences, explanations, or conversational filler. Never repeat the question's phrasing or append contextual modifiers to the answer.
- **Minimal Reasoning**: Skip verbose derivations for straightforward retrieval tasks. If step-by-step reasoning is performed, place it outside the answer tags and keep it brief.
