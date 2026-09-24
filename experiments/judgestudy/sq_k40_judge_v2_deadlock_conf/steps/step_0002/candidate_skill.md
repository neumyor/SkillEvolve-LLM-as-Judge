# Question Answering Skill

# Question Answering Skill

## Clue & Fragment Interpretation
- **Trivia/Jeopardy Format**: Questions often appear as clues, definitions, or sentence fragments. Treat them as prompts to identify the specific entity, term, or concept that completes the statement.
- **Ignore Conversational Framing**: Strip away introductory phrases or conversational wrappers. Focus on the core factual query.

## Search & Extraction Strategy
- **Identifier Focus**: Extract core keywords (names, locations, dates, unique phrases) from the question. Map these directly to the `[DOC]`/`[PAR]` blocks.
- **Direct Span Retrieval**: Scan context for verbatim or near-verbatim matches to the clue. Prioritize passages where the question phrasing appears alongside its answer.
- **Cross-Snippet Validation**: When multiple passages discuss the same topic, cross-reference details to ensure consistency. Resolve contradictions by favoring explicit statements over implied ones.
- **Grounding Constraint**: Only extract answers explicitly stated or strongly implied in the provided context. Avoid external knowledge substitution or guessing.

## Answer Precision & Format Rules
- **Minimal Span Extraction**: Extract the shortest text span that directly answers the question. Never append descriptive nouns, roles, or adjectives (e.g., use 'Madge' not 'Madge the Manicurist', 'Arthur' not 'Chester A. Arthur', 'pudding' not 'Hasty pudding').
- **Name Granularity**: Match the name format implied by the question. If the clue references a surname or first name alone, return that alone. Include honorifics (e.g., 'Sir') only if they are standardly attached to the name in the context.
- **Category vs. Example**: Do not substitute a specific example mentioned in the text for a general category (or vice versa) unless explicitly asked. Stick to the exact term targeted by the clue.
- **Tag Enforcement**: Place all final answers strictly within `<answer>...</answer>` tags. Omit reasoning, greetings, or filler inside the tags. Provide step-by-step reasoning outside the tags if helpful.
