# Question Answering Skill

## Core Analytical Strategies
- **Keyword & Clue Anchoring**: Scan the question for distinctive markers (dates, names, numbers, unique phrases) and Jeopardy-style descriptors. Use these as anchors to quickly locate the relevant `[DOC]` passages.
- **Reference Resolution**: When questions contain demonstratives or possessives (e.g., "this country", "its"), explicitly identify the exact entity they refer to in the context before formulating the answer.
- **Multi-Document Cross-Verification**: If multiple passages address the question, scan all relevant documents to confirm facts and resolve ambiguities. Prefer the most direct or consistently stated match.

- **Placeholder & Cloze Parsing**: Treat generic pointers (e.g., "this film", "a [adjective] dessert") and Jeopardy-style fragments as direct fill-in-the-blank requests. Map category hints directly to the specific subject named in the context.
- **Temporal & Qualifier Awareness**: Scrutinize historical markers, superlatives (e.g., 'largest', 'first'), and dates. These qualifiers often distinguish between past/present entities, renamed locations, or similar namesakes.
- **Heading & Snippet Prioritization**: For trivia queries, scan document titles (`[TLE]`) and opening snippets first. These often contain the exact answer or direct paraphrase, anchoring your search before diving into paragraphs.
- **Distractor Filtering**: When context contains quiz pairs, forums, or mixed snippets, explicitly ignore incorrect guesses, anecdotes, or tangential details. Anchor strictly to definitive factual statements.

## Answer Extraction Rules
- **Strict Conciseness**: Output only the exact entity, word, or short phrase requested. Never include full sentences, explanations, or conversational filler inside `<answer>...</answer>`.
- **Trivia/Fragment Handling**: Treat incomplete sentences or clue-like questions as direct requests for a missing keyword. Identify the target entity immediately without describing relationships or generating categories.
- **Exact Term Preference**: Prioritize the exact term found in the context over synonyms, acronyms, or full names. If the context uses "C", answer "C". If it uses "Genet", answer "Genet". Only expand if explicitly asked.

- **Grammatical & Structural Fidelity**: Strictly match the grammatical form implied by the question. Provide only the surname if asked for a name, avoid plurals if a singular term is requested, and omit articles unless integral to the term. Never add middle initials or expand names beyond what the question demands.
- **Concept Over Example**: For clue-like, Jeopardy-style, or definition-seeking questions, identify the overarching category, function, or concept. Do not default to a specific instance or example from the text unless the question explicitly asks for one.
- **Zero Reasoning in Tags**: Perform all analysis and step-by-step thinking before the `<answer>` tag. The content inside the tags must be the final answer only.

## Execution Workflow
1. Read the question and highlight key identifiers or descriptive clues.
2. Search the context for those identifiers or their immediate synonyms. Ignore irrelevant tangential documents.
3. Provide a concise, single-sentence verification trace (e.g., "Based on the provided context...") only if synthesis or disambiguation is required. Skip extended analysis for straightforward matches to prevent verbosity.
4. Output only the core answer inside `<answer>...</answer>` tags.
