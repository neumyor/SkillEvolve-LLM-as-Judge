# Question Answering Skill

## Core Analytical Strategies
- **Keyword & Clue Anchoring**: Scan the question for distinctive markers (dates, names, numbers, unique phrases) and Jeopardy-style descriptors. Use these as anchors to quickly locate the relevant `[DOC]` passages.
- **Reference Resolution**: When questions contain demonstratives or possessives (e.g., "this country", "its"), explicitly identify the exact entity they refer to in the context before formulating the answer.

- **Cloze & Definition Mapping**: Treat fragment questions as direct definition requests. Locate the exact sentence matching the clue and extract the subject term verbatim.
- **Primary Subject Isolation**: When multiple entities are mentioned, isolate the one that directly satisfies the question's descriptor. Ignore tangential examples, historical anecdotes, or secondary mentions to prevent over-specification.
- **Semantic Paraphrase Mapping**: Questions frequently rephrase factual statements using synonyms, descriptors, or cloze-style blanks. Map the question's descriptive phrasing directly to the exact terminology in the `[DOC]` passages before extraction.
- **Multi-Document Cross-Verification**: If multiple passages address the question, scan all relevant documents to confirm facts and resolve ambiguities. Prefer the most direct or consistently stated match.

## Answer Extraction Rules
- **Strict Conciseness**: Output only the exact entity, word, or short phrase requested. Never include full sentences, explanations, or conversational filler inside `<answer>...</answer>`.
- **Trivia/Fragment Handling**: Treat incomplete sentences, Jeopardy-style clues, and declarative statement prompts (e.g., 'It's the...', 'This [noun]...') as direct fill-in-the-blank or definition requests. Ignore non-semantic tokens like trailing clue numbers, colons, or parentheses. Identify the target entity immediately without describing relationships or generating categories.
- **Exact Term Preference**: Prioritize the exact term found in the context over synonyms, acronyms, or full names. If the context uses "C", answer "C". If it uses "Genet", answer "Genet". Only expand if explicitly asked.
- **Zero Reasoning in Tags**: Perform all analysis and step-by-step thinking before the `<answer>` tag. The content inside the tags must be the final answer only.

## Execution Workflow
1. Read the question and highlight key identifiers or descriptive clues.
2. Search the context for those identifiers or their immediate synonyms. Ignore irrelevant tangential documents.
3. Provide a concise, single-sentence grounded justification that directly links the question's clue to the extracted entity, confirming context alignment. Skip extended analysis for straightforward trivia queries to prevent verbosity.
4. Output only the core answer inside `<answer>...</answer>` tags.

- **Entity Type & Form Alignment**: Parse the question to identify the exact entity type requested (e.g., territory, sport, species). Answer strictly with that entity, avoiding tangential details or related institutions. Strictly preserve the exact grammatical form (singular/plural), retain all necessary modifiers, and output the complete compound term (e.g., 'Brown pelican', 'the South Sea Bubble') as it appears in the context. Do not truncate, expand, or substitute with synonyms.
