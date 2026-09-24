# Success Memory Item 1
## Title
Interpret Sentence-Fragment Queries as Direct Entity Requests
## Description
Treat incomplete sentences, trivia clues, or crossword-style prompts as direct requests for a missing key term, focusing extraction on the grammatical or semantic slot left open by the fragment.
## Content
Identify the core subject and defining descriptor in the prompt (e.g., "programming language," "named for... Blaise"). Scan the retrieved context for the exact term that logically completes the relationship, bypassing the need to reconstruct full interrogative sentences or parse conversational filler.

# Success Memory Item 2
## Title
Resolve Partial Identifiers Using Contextual Anchors
## Description
When a prompt supplies only a first name, abbreviation, or partial identifier, use accompanying domain-specific descriptors to pinpoint the correct full entity before extracting the target answer.
## Content
Cross-reference the partial name with contextual markers (e.g., profession, invention, era, or field) to confirm the complete entity. Once resolved, trace the explicit link in the text to the requested attribute, ensuring the extracted term directly satisfies the prompt's naming or attribution constraint.

# Success Memory Item 3
## Title
Isolate Final Answer Within Required XML Tags
## Description
Separate internal reasoning from the final output by strictly confining the answer to the designated tag format, ensuring compatibility with automated parsing and grading systems.
## Content
After verifying the extracted term aligns with the context, output only the formatted string (`<answer>Term[/answer]`). Exclude all explanatory text, confidence checks, or conversational phrases from the final response block to maintain strict compliance with task specifications.
