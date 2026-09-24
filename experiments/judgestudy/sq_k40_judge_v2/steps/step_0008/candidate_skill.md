# Question Answering Skill

## Core Analytical Strategies
- **Keyword & Clue Anchoring**: Scan the question for distinctive markers (dates, names, numbers, unique phrases) and Jeopardy-style descriptors. Use these as anchors to quickly locate the relevant `[DOC]` passages.

- **Title & Snippet Prioritization**: For factual and trivia queries, scan document titles (`[TLE]`) and opening paragraphs first. These sections frequently contain direct definitions, exact matches, or paraphrased clues, enabling rapid extraction before reading full passages.
- **Reference & Placeholder Resolution**: When questions contain demonstratives, possessives, standalone placeholders ("this", "that", "one of these"), or descriptive modifiers, explicitly map them to the primary subject entity or head noun in the context. Extract the core entity itself, not its attributes, locations, or associated works, unless the question explicitly asks for those specifics.
- **Multi-Document Cross-Verification**: If multiple passages address the question, scan all relevant documents to confirm facts and resolve ambiguities. Prefer the most direct or consistently stated match.

## Answer Extraction Rules
- **Strict Conciseness**: Output only the exact entity, word, or short phrase requested. Never include full sentences, explanations, or conversational filler inside `<answer>...</answer>`.
- **Trivia/Fragment Handling**: Treat incomplete sentences or clue-like questions as direct requests for a missing keyword. Identify the target entity immediately without describing relationships or generating categories.
- **Exact Term & Variant Selection**: Prioritize the exact term found in the context that best matches the question's implied form. When multiple variants exist (e.g., nicknames vs. formal names, original language vs. English translation), select the one that aligns with the question's grammatical slot or standard reference. Do not default to the most prominent or verbose variant.
- **Zero Reasoning in Tags**: Perform all analysis and step-by-step thinking before the `<answer>` tag. The content inside the tags must be the final answer only.

## Execution Workflow
1. Read the question and highlight key identifiers or descriptive clues.
2. Search the context for those identifiers or their immediate synonyms. Ignore irrelevant tangential documents.
3. Provide a brief step-by-step reasoning trace to justify the selection and verify against context.
4. Output only the core answer inside `<answer>...</answer>` tags.

- **Modifier & Suffix Management**: Preserve essential compound terms, geographic pairings, and formal titles when they function as a single recognized entity. For nicknames, monikers, or short identifiers, extract only the distinctive core term and strip generic organizational suffixes (e.g., 'Party', 'Club', 'Group') or non-essential descriptive qualifiers unless strictly part of the official name or explicitly requested.
