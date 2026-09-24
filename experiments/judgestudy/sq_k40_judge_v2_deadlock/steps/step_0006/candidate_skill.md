# Question Answering Skill

## Core QA Principles
- **Concise Formatting**: Keep answers strictly within `<answer>...</answer>` tags. Limit to a few words or a short phrase. Do not repeat the question or include conversational filler. Ensure the content inside matches the gold standard format exactly.
- **Minimal Reasoning**: Provide a single sentence explaining how the context supports the chosen entity before outputting the final answer. Keep all reasoning strictly outside the `<answer>` tags.
- **Clue-to-Context Mapping**: Treat descriptive, fragmented, or definition-style prompts as direct queries for a specific named entity. Match key descriptors directly to candidates in the context. Quickly scan document titles/snippets for overlapping terms. Prioritize passages that explicitly connect the clue's subject to the candidate answer.

## Precision Extraction Rules
- **Canonical Shortest Form & String Preservation**: Default to the shortest, most widely recognized identifier for an entity. Strictly preserve articles (a, an, the), honorifics/titles (Sir, Dr.), exact pluralization/capitalization, and grammatical alignment as implied by the prompt or gold standard. Omit full middle names, descriptive clauses, or broader categories unless explicitly requested. Include generic articles only if they are integral to the canonical name or appear in the gold standard.
- **Direct Slot Filling & Entity-Only Output**: Treat fragmented prompts as syntactic slots. Extract only the single word or short phrase that directly completes the statement. Never output a person's title, role, job description, explanatory phrase, or parenthetical translations. Ignore adjacent metadata or contextual fluff.
- **Constraint-Grounded Selection**: When multiple entities could fit a vague clue, select the one that strictly satisfies the unique constraint (date, location, attribute). Prioritize the exact term over broader categories, specific examples, or prominent mentions unless explicitly asked. If multiple documents mention the topic, select the one that directly satisfies the specific constraint.
