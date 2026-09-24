# Success Memory Item 1
## Title
Constraint-to-Text Mapping
## Description
Align explicit question parameters with retrieved document phrases to isolate candidate answers.
## Content
Parse the query for defining attributes (e.g., value ratios, timeframes, geographic markers) and scan context snippets for exact or synonymous matches. Prioritize documents where multiple constraints co-occur in a single sentence to maximize precision.

# Success Memory Item 2
## Title
Cross-Source Consensus
## Description
Validate candidate terms by checking agreement across multiple independent retrieval results.
## Content
When several documents independently point to the same entity using consistent phrasing, treat this convergence as strong evidence. Avoid overcomplicating the answer when redundant sources confirm a single, unambiguous term.

# Success Memory Item 3
## Title
Strict Output Formatting
## Description
Deliver the final extracted term using only the mandated container tags, omitting explanatory text.
## Content
Once the target entity is confirmed, strip all surrounding context, reasoning, or qualifiers. Wrap only the exact noun or phrase in the required tags to ensure compatibility with automated grading systems and maintain conciseness.
