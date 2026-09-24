# Question Answering Skill

## Core Analytical Strategies
- **Keyword & Clue Anchoring**: Scan the question for distinctive markers (dates, names, numbers, unique phrases) and Jeopardy-style descriptors. Use these as anchors to quickly locate the relevant `[DOC]` passages.
- **Reference Resolution**: When questions contain demonstratives or possessives (e.g., "this country", "its"), explicitly identify the exact entity they refer to in the context before formulating the answer.
- **Multi-Document Cross-Verification**: If multiple passages address the question, scan all relevant documents to confirm facts and resolve ambiguities. Prefer the most direct or consistently stated match.

- **Context Noise Filtering**: When contexts contain mixed snippets (e.g., recipe blogs, forum comments, book reviews), explicitly ignore conversational framing, personal anecdotes, and tangential mentions. Anchor strictly to definitive factual statements or direct definitions that name the target entity.

- **Primary Subject Isolation**: When contexts mention multiple related entities, isolate the one that directly satisfies the question's descriptor. Ignore tangential examples, historical anecdotes, or secondary mentions to prevent over-specification.

## Answer Extraction Rules
- **Strict Conciseness**: Output only the exact entity, word, or short phrase requested. Never include full sentences, explanations, or conversational filler inside `<answer>...</answer>`.
- **Trivia/Fragment Handling**: Treat incomplete sentences or clue-like questions as direct requests for a missing keyword. Identify the target entity immediately without describing relationships or generating categories.

- **Minimal Entity & Descriptor Pruning**: For short, fragmentary, or keyword-only questions, extract only the single core entity or exact term. Strip all descriptive clauses, temporal markers, titles, and generic categories. Default to the shortest direct name that uniquely satisfies the query. Never output multi-word descriptions unless they form a fixed proper name. Strictly preserve indefinite/definite articles ('a', 'an', 'the') and singular/plural forms; do not alter number agreement or strip articles to force conciseness.
- **Exact Term Preference**: Prioritize the exact term found in the context over synonyms, acronyms, or full names. If the context uses "C", answer "C". If it uses "Genet", answer "Genet". Only expand if explicitly asked.

- **Category Constraint Enforcement**: When the question specifies a noun class or type (e.g., 'this acid', 'these birds'), strictly filter candidate entities to match that semantic constraint. Ignore closely related terms that share keywords but belong to a different category (e.g., reject 'soda' when the clue explicitly asks for an 'acid').
- **Zero Reasoning in Tags**: Perform all analysis and step-by-step thinking before the `<answer>` tag. The content inside the tags must be the final answer only.

## Execution Workflow
1. Read the question and highlight key identifiers or descriptive clues.
2. Search the context for those identifiers or their immediate synonyms. Ignore irrelevant tangential documents.
3. Provide a brief step-by-step reasoning trace to justify the selection and verify against context.
4. Output only the core answer inside `<answer>...</answer>` tags.
