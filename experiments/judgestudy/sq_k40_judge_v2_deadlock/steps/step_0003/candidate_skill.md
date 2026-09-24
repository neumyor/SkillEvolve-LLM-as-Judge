# Question Answering Skill

## Core QA Strategy
- **Clue-to-Context Mapping**: Treat descriptive, fragmented, or definition-style prompts as direct queries for a specific named entity. Match key descriptors directly to candidates in the context.
- **Keyword Scanning**: Quickly scan document titles and snippets for terms overlapping with the question's clue. Iterate through `[DOC]` passages for exact matches or strong semantic overlaps.
- **Explicit Link Verification**: Prioritize passages that explicitly connect the clue's subject to the candidate answer. If multiple documents mention the topic, select the one that directly satisfies the specific constraint (date, location, or attribute).
- **Abstract vs. Concrete Targeting**: When a question describes a function, category, property, or role, extract the abstract category or functional term. Do not answer with a list of concrete instances unless explicitly asked.

## Precision Extraction Rules
- **Exact Match Priority**: Output only the precise word, short phrase, or entity requested. Never add descriptions, parenthetical translations, explanatory clauses, or "Yes/No" verdicts unless explicitly asked.
- **Grammatical & Specificity Alignment**: Strictly match the exact number (singular/plural), capitalization, and specificity of the target. If the context or expected answer uses a specific term (e.g., "Brown pelican", "Pineapples"), output that exact string. Do not generalize or simplify. Default to surnames or shortest widely recognized identifiers unless a full name is requested. Preserve exact capitalization and hyphenation.
- **Constraint Targeting**: Carefully parse the question's grammatical subject and object to determine exactly what is being asked (e.g., location, time period, institution vs. territory). Extract only the entity that satisfies the specific constraint, ignoring closely related but incorrect entities.
- **Avoid Unnecessary Expansions**: If the expected answer is a single letter, abbreviation, surname, or title, output only that. Omit articles (a, an, the), plural suffixes, or conversational filler.
- **Fragmented Query Resolution**: For truncated, typo-ridden, or incomplete prompts, isolate the key descriptive clues and map them directly to the most salient factual answer in the context. Prioritize direct entity matches over inferred relationships. Infer missing keywords directly from the context and output concisely.

## Formatting & Reasoning Constraints
- **Strict Tagging**: Always wrap the final answer in `<answer>...</answer>`. Ensure the content inside matches the gold standard format (typically a single entity or short phrase).
- **Concise Output**: Limit answers to a few words or a short phrase. Omit restatements of the question or introductory phrases.
- **Minimal Reasoning**: Provide a single sentence explaining how the context supports the chosen entity before outputting the final answer. Keep all reasoning strictly outside the `<answer>` tags.
