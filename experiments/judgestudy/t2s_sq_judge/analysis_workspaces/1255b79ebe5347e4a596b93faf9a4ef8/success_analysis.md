# Success Memory Item 1
## Title
Phrase-Matching Anchoring
## Description
Leverage distinctive descriptors or nicknames from the question as search anchors to quickly locate the exact supporting sentence in retrieved context.
## Content
When a question contains unique phrasing (e.g., "sweetheart," "known as," "famous for"), scan the context for those exact terms or close lexical matches. This bypasses irrelevant documents and isolates the precise sentence containing the answer.

# Success Memory Item 2
## Title
Syntactic Entity Isolation
## Description
Extract the target answer by identifying the proper noun or subject directly linked to the anchored phrase within the same clause.
## Content
Once the anchor phrase is located, trace the immediate grammatical relationship to find the named entity. Prioritize nouns appearing right before or after the descriptor (e.g., "actress [Name] who was dubbed...") to ensure accurate extraction without overcomplicating the selection.

# Success Memory Item 3
## Title
Constraint-Driven Formatting
## Description
Apply strict structural rules to the final output to guarantee compatibility with automated evaluation systems.
## Content
Immediately wrap the isolated entity in the required tags without adding conversational filler or external explanations. Maintain a direct pipeline from extraction to formatted output to prevent parsing failures and preserve scoring accuracy.
