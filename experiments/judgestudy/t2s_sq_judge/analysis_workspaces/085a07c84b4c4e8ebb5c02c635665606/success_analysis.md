# Success Memory Item 1
## Title
Relational & Locational Clue Decomposition
## Description
Parse trivia-style prompts into explicit relational and geographic keywords to anchor targeted document scanning.
## Content
Break the question into distinct identifiers (e.g., "relative of [X]", "found in [Y]"). Use these as search anchors within the retrieved context to locate sentences that explicitly connect the clues to a single target entity, ensuring the selected answer satisfies all prompt conditions simultaneously.

# Success Memory Item 2
## Title
Direct Contextual Extraction
## Description
Ground the final answer strictly in the provided text by isolating the exact entity name linked to the identifying clues.
## Content
When the context contains a direct statement matching the prompt's keywords, extract that exact noun phrase as the answer. Rely solely on the explicit textual match rather than external knowledge or inference, which maintains factual alignment and minimizes hallucination risk.

# Success Memory Item 3
## Title
Concise Entity Normalization
## Description
Select the most direct, commonly recognized term when multiple valid variants exist in the source material.
## Content
If the context offers several acceptable names (e.g., regional subspecies vs. common genus), default to the shortest, most widely understood term that fits the prompt's grammatical structure. This prevents over-specification while preserving accuracy and adhering to output length constraints.
