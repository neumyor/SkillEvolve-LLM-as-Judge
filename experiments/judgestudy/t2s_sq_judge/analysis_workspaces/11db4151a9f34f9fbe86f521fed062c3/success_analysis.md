# Success Memory Item 1
## Title
Extract Explicit Query Anchors
## Description
Decompose the prompt into discrete numerical, temporal, and categorical constraints to establish precise matching criteria.
## Content
Ignore narrative framing and isolate hard metrics (e.g., team tenure, specific statistical totals, record counts). Treat these values as non-negotiable filters for scanning retrieved documents.

# Success Memory Item 2
## Title
Triangulate via Multi-Snippet Consensus
## Description
Synthesize overlapping partial matches across multiple context passages to identify the single entity that satisfies all extracted constraints.
## Content
When individual snippets only cover fragments of the query, map each fragment to its corresponding source. If disparate passages consistently point to the same subject when combined with the anchor metrics, accept that subject as the definitive match.

# Success Memory Item 3
## Title
Enforce Strict Output Schema
## Description
Translate the resolved entity directly into the mandated response format, stripping all intermediate reasoning before submission.
## Content
Once the target entity is confirmed through cross-document alignment, bypass explanatory text. Wrap only the final identifier in the specified tags (e.g., `<answer>...</answer>`) to guarantee structural compliance.
