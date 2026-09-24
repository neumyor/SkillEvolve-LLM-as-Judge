# Question Answering Skill

## Core QA Strategy
- **Clue-to-Context Mapping**: Treat descriptive, fragmented, or Jeopardy-style prompts as direct queries for a specific named entity. Match key descriptors directly to candidates in the context.
- **Keyword Scanning**: Quickly scan document titles and snippets for terms overlapping with the question's clue. Iterate through `[DOC]` passages for exact matches or strong semantic overlaps.
- **Explicit Link Verification**: Prioritize passages that explicitly connect the clue's subject to the candidate answer. If multiple documents mention the topic, select the one that directly satisfies the specific constraint (date, location, or attribute).

## Precision Extraction Rules
- **Exact Short Phrase Priority**: For trivia, Jeopardy-style, or definition prompts, output *only* the target entity or short phrase. Never output descriptive sentences, full explanations, or conversational filler.
- **Name & Title Normalization**: Strictly match the canonical form of names. Automatically strip middle initials/letters (e.g., "B."), suffixes (e.g., "Jr.", "Sr."), and generic location descriptors (e.g., "Desert", "Base", "Plant") unless the question explicitly asks for them. Preserve exact capitalization.
- **Constraint-Grounded Selection**: Carefully map each clue in the question to the specific entity in the context. Avoid defaulting to the most prominent or frequently mentioned entity; prioritize the one that precisely fits the unique constraint or implied reference.
- **Grammatical & Specificity Alignment**: Strictly match the exact number (singular/plural), capitalization, and specificity of the target. Default to surnames or shortest widely recognized identifiers unless a full name is requested. Preserve exact capitalization and hyphenation.
- **Avoid Unnecessary Expansions**: If the expected answer is a single letter, abbreviation, surname, or title, output only that. Omit articles (a, an, the), plural suffixes, or conversational filler. When a question describes a function, category, property, or role, extract the abstract category or functional term. Do not answer with a list of concrete instances unless explicitly asked.

## Formatting & Reasoning Constraints
- **Strict Tagging**: Always wrap the final answer in `<answer>...</answer>`. Ensure the content inside matches the gold standard format (typically a single entity or short phrase).
- **Concise Output**: Limit answers to a few words or a short phrase. Omit restatements of the question or introductory phrases.
- **Minimal Reasoning**: Provide a single sentence explaining how the context supports the chosen entity before outputting the final answer. Keep all reasoning strictly outside the `<answer>` tags.
