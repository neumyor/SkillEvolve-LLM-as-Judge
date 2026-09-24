# Question Answering Skill

## Answer Extraction Rules (Priority for Trivia & Exact Matches)
- **Exact Match Priority**: For trivia, Jeopardy-style, or fill-in-the-blank questions, output the *exact* word or short phrase requested. Do not paraphrase or add descriptive clauses.
- **Avoid Expansions & Full Names**: If the expected answer is a single letter, abbreviation, or surname, output only that. Do not expand "C" to "Vitamin C" or "Genet" to "Jean Genet" unless the question explicitly asks for the full name.
- **Direct Entity Response**: When a question asks for a person, band, place, or object, provide only the entity name. Do not answer with "Yes/No", descriptions (e.g., "a tribute band"), or full sentences.
- **Partial Query Handling**: For fragmented questions (e.g., lyrics, titles, or incomplete statements), infer the missing keyword directly from the context and output it concisely.

## Core QA Principles & Strategy
- **Concise Formatting**: Keep answers strictly within `<answer>...</answer>` tags. Limit to a few words or a short phrase. Do not repeat the question or include conversational filler.
- **Clue-to-Context Mapping**: Treat descriptive or incomplete-sentence questions as clues. Match key descriptors directly to named entities in the context.
- **Minimal Reasoning**: Provide a single sentence explaining how the context supports the chosen entity before outputting the final answer.
- **Keyword Scanning**: Quickly scan document titles and snippets for terms overlapping with the question's clue. Iterate through all `[DOC]` passages for exact matches or strong semantic overlaps.
- **Explicit Link Verification**: Prioritize passages that explicitly connect the clue's subject to the candidate answer. If multiple documents mention the topic, select the one that directly satisfies the specific constraint (date, location, or attribute).
- **Handle Quotes & Paraphrases**: If the question contains a partial quote or translated phrase, locate its counterpart in the context to identify the target answer.
- **Strict Conciseness**: Once the target information is identified, extract only the precise entity, name, or short phrase. Omit full sentences, conversational filler, or restatements of the question.
