# Success Memory Item 1
## Title
Anchor Queries on Distinctive Quoted Phrases
## Description
Treat unique, verbatim phrases in the prompt as primary retrieval anchors to quickly locate the exact context snippet containing the answer.
## Content
When a question includes a highly specific quote or descriptor, prioritize exact-string matching against retrieved documents. This bypasses broad semantic filtering and isolates the precise passage where the target entity is named, significantly reducing search space and cognitive load.

# Success Memory Item 2
## Title
Direct Extraction from Explicit Contextual Links
## Description
Immediately extract the associated entity once the context explicitly connects the query's key phrase to a specific subject, avoiding unnecessary synthesis.
## Content
If a retrieved passage directly pairs the prompt's unique phrasing with a name or term, treat that pairing as definitive. Skip additional reasoning steps or external validation; simply pull the linked entity to preserve accuracy and prevent hallucination or overcomplication.

# Success Memory Item 3
## Title
Strict Delimiter Enforcement for Evaluation Compatibility
## Description
Isolate the final answer within the required tags, completely excluding explanatory text or conversational framing to ensure automated parsers succeed.
## Content
Automated grading systems typically rely on regex or exact-match algorithms targeting specific tags. Wrapping only the core answer in the designated delimiters guarantees that formatting requirements do not trigger false negatives, regardless of the underlying factual correctness.
