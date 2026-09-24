# Success Memory Item 1
## Title
Direct Identifier Association
## Description
Map unique terms, nicknames, or highly specific phrases from the prompt directly to their corresponding entities in the retrieved context.
## Content
Scan documents for exact or near-exact matches of distinctive identifiers. When a context fragment explicitly pairs the unique term with a candidate name, treat that direct linkage as the primary evidence. Avoid unnecessary multi-step reasoning when the association is stated outright.

# Success Memory Item 2
## Title
Cross-Snippet Consistency Validation
## Description
Confirm the target entity by checking for repeated associations across multiple independent context fragments.
## Content
Compare different retrieved snippets to see if they consistently point to the same entity for the given identifier. High agreement across varied sources (e.g., historical summaries, trivia databases, crossword archives) strongly indicates correctness. Flag and discard candidates if conflicting associations emerge.

# Success Memory Item 3
## Title
Constraint-Aligned Extraction
## Description
Format the final answer strictly according to prompt specifications, prioritizing brevity and delimiter compliance.
## Content
After isolating the correct entity, audit it against explicit output rules (e.g., short phrase only, specific XML tags, no trailing punctuation). Remove any contextual framing or explanatory text. Ensure the enclosed string stands alone and matches the exact structural requirements before submission.
