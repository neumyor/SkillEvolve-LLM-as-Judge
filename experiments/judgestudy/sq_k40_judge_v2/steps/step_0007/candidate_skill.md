# Question Answering Skill

## Core Analytical Strategies
- **Keyword & Clue Anchoring**: Scan the question for distinctive markers (dates, names, numbers, unique phrases) and Jeopardy-style descriptors. Use these as anchors to quickly locate the relevant `[DOC]` passages.
- **Reference Resolution**: When questions contain demonstratives or possessives (e.g., "this country", "its"), explicitly identify the exact entity they refer to in the context before formulating the answer.

- **Slot & Role Alignment**: Identify the exact semantic role requested by the question (e.g., person, location, concept). Do not default to adjacent nouns or descriptive phrases mentioned in the clue. If the question asks for 'he' or 'this site', extract the subject/entity itself, not associated objects or attributes.
- **Multi-Document Cross-Verification**: If multiple passages address the question, scan all relevant documents to confirm facts and resolve ambiguities. Prefer the most direct or consistently stated match.

## Answer Extraction Rules
- **Strict Conciseness**: Output only the exact entity, word, or short phrase requested. Never include full sentences, explanations, or conversational filler inside `<answer>...</answer>`.
- **Jeopardy, Cloze & Definition Mapping**: Treat fragmentary, Jeopardy-style, declarative clues, definitions, slogans, and trailing blanks as direct fill-in-the-blank requests. Isolate the core subject entity being described, strictly ignoring tangential attributes, genres, or secondary examples. Map the clue's descriptive phrasing directly to the exact terminology in the `[DOC]` passages.
- **Exact Term & Grammatical Fidelity**: Extract the exact term matching the question's grammatical slot. Strictly preserve singular/plural forms, parts of speech, and capitalization. Drop generic geographic or descriptive suffixes (e.g., 'Island', 'River') unless they are integral to the official name or explicitly required. Match the expected entity's precise morphological form.
- **Zero Reasoning in Tags**: Perform all analysis and step-by-step thinking before the `<answer>` tag. The content inside the tags must be the final answer only.

## Execution Workflow
1. Read the question and highlight key identifiers or descriptive clues.
2. Search the context for those identifiers or their immediate synonyms. Ignore irrelevant tangential documents.
3. Provide a concise verification trace that explicitly quotes the exact sentence or phrase from the context confirming the answer. Directly link the question's core descriptor to this textual evidence before extracting the final term.
4. Output only the core answer inside `<answer>...</answer>` tags.
