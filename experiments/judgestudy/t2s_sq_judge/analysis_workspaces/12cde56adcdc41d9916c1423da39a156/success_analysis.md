# Success Memory Item 1
## Title
Direct Keyword Co-occurrence Extraction
## Description
Scan retrieved documents for explicit phrase matches linking the prompt's core concepts to isolate the target entity.
## Content
When answering factual identification questions, prioritize locating sentences that directly pair the question's key terms (e.g., "birds choose their mates" and "holiday"). Extract the answer verbatim from these high-signal snippets rather than synthesizing or inferring from peripheral context.

# Success Memory Item 2
## Title
Cross-Documenary Signal Convergence
## Description
Leverage agreement across multiple independent context snippets to solidify the extracted answer without additional search steps.
## Content
If several retrieved documents independently highlight the same entity or fact, treat this internal consistency as definitive. Relying on multi-source alignment within the initial retrieval batch streamlines decision-making and eliminates the need for iterative querying.

# Success Memory Item 3
## Title
Nominal Variant Normalization
## Description
Recognize and map minor naming differences to a single canonical answer when they reference the same real-world entity.
## Content
During extraction, account for contextual variations in how an entity is named (e.g., "Valentine's Day" vs. "St. Valentine's Day"). Treat these as functionally equivalent and output the most common or concise form to prevent unnecessary formatting mismatches.
