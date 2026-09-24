# Success Memory Item 1
## Title
Keyword-Driven Entity Mapping
## Description
Translate distinctive prompt qualifiers into search anchors to locate the target entity within retrieved passages.
## Content
Isolate unique descriptors from the question (e.g., temporal markers, geographic origins, activity types, social demographics). Scan the context corpus for sentences that simultaneously contain these qualifiers. When a single named concept consistently satisfies all descriptive constraints, flag it as the primary candidate.

# Success Memory Item 2
## Title
Cross-Passage Corroboration
## Description
Confirm candidate accuracy by ensuring multiple independent context snippets independently support the same identification.
## Content
Do not finalize an answer based on a single isolated match. Check that at least two separate retrieved documents describe the same entity using the prompt's defining characteristics. Converging evidence eliminates false positives caused by coincidental keyword overlap and solidifies the selection.

# Success Memory Item 3
## Title
Constraint-Aligned Output Stripping
## Description
Remove all reasoning, context, and auxiliary text to deliver only the exact target string inside the required delimiters.
## Content
Once the correct entity is confirmed, extract the bare proper noun or term. Discard surrounding explanations, dates, or descriptive modifiers. Wrap solely the isolated term in the specified tag format to guarantee strict compliance with automated evaluation pipelines.
