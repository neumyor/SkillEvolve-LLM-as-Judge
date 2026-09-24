# Success Memory Item 1
## Title
Targeted Descriptor Matching for Entity Resolution
## Description
Leverage precise quantitative or geographic clues from the prompt to scan and align with corresponding phrases in retrieved context, enabling rapid identification of the correct entity.
## Content
When a question contains specific attributes (e.g., distance, location type, connecting infrastructure), search the retrieved documents for exact or semantically equivalent phrasing. Prioritize snippets that directly pair these descriptors with a proper noun, as they typically yield the answer through straightforward lexical overlap rather than complex inference.

# Success Memory Item 2
## Title
Multi-Snippet Consensus Filtering
## Description
Strengthen entity selection by cross-checking multiple independent context passages for consistent attribution of the target clues to the same name.
## Content
After identifying a candidate in one passage, quickly scan related documents to verify that they independently associate the same descriptive features with the identical entity. This consensus approach reduces ambiguity and accelerates decision-making when multiple sources cover overlapping factual ground.

# Success Memory Item 3
## Title
Constraint-Aligned Output Formatting
## Description
Eliminate all reasoning and conversational text from the final response, strictly wrapping only the resolved entity in the mandated output tags.
## Content
Once the target entity is confirmed, bypass explanatory steps entirely. Directly place the single correct term or phrase inside the required XML-style markers (e.g., `<answer>...</answer>`), ensuring strict compliance with parsing rules and preventing format rejection or token waste.
