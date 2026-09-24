# Question Answering Skill

## Core Analytical Strategies
- **Keyword & Clue Anchoring**: Scan the question for distinctive markers (dates, names, numbers, unique phrases) and Jeopardy-style descriptors. Use these as anchors to quickly locate the relevant `[DOC]` passages.

- **Snippet & Title Leverage**: For trivia and factual queries, prioritize scanning document titles (`[TLE]`) and opening snippets first. These sections frequently contain direct definitions, exact matches, or paraphrased clues, enabling rapid extraction before reading full paragraphs.
- **Reference Resolution**: When questions contain demonstratives or possessives (e.g., "this country", "its"), explicitly identify the exact entity they refer to in the context before formulating the answer.
- **Multi-Document Cross-Verification**: If multiple passages address the question, scan all relevant documents to confirm facts and resolve ambiguities. Prefer the most direct or consistently stated match.

- **Constraint-Driven Filtering**: When contexts contain mixed snippets, tangential details, or multiple candidate entities, explicitly ignore loosely matching items. Anchor strictly to the entity that satisfies the most restrictive clues (e.g., exact dates, unique actions) simultaneously.

## Answer Extraction Rules
- **Strict Conciseness**: Output only the exact entity, word, or short phrase requested. Never include full sentences, explanations, or conversational filler inside `<answer>...</answer>`.
- **Trivia/Fragment Handling**: Treat incomplete sentences or clue-like questions as direct requests for a missing keyword. Identify the target entity immediately without describing relationships or generating categories.
- **Exact Term Preference**: Prioritize the exact term found in the context over synonyms, acronyms, or full names. If the context uses "C", answer "C". If it uses "Genet", answer "Genet". Only expand if explicitly asked.
- **Zero Reasoning in Tags**: Perform all analysis and step-by-step thinking before the `<answer>` tag. The content inside the tags must be the final answer only.

- **Subject Over Attribute Mapping**: For Jeopardy-style fragments or cloze blanks, identify the core subject entity being described, not its attributes, genres, titles, or mediums. If the clue describes a property (e.g., "made of rubber", "based on a play"), extract the primary noun/category (e.g., "bubble gum", "Romeo and Juliet") rather than descriptive adjectives or related concepts.
- **Entity Form & Name Fidelity**: Match the exact grammatical form and length of the expected entity. Avoid truncating essential modifiers or compound terms (e.g., keep "Forbes magazine" if that is the standard reference). Do not over-expand to verbose formal names unless explicitly required. Anchor to the shortest, most direct entity name that uniquely satisfies the query.

## Execution Workflow
1. Read the question and highlight key identifiers or descriptive clues.
2. Search the context for those identifiers or their immediate synonyms. Ignore irrelevant tangential documents.
3. Provide a concise, single-sentence verification trace linking the question's core descriptors to the extracted entity. Skip extended analysis or multi-step breakdowns for straightforward trivia matches to maintain speed and conciseness.
4. Output only the core answer inside `<answer>...</answer>` tags.
