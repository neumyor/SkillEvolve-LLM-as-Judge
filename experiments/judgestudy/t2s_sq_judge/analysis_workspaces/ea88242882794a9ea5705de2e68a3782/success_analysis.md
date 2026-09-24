# Success Memory Item 1
## Title
Syntactic Phrase Matching for Target Extraction
## Description
Align question structure with explicit context phrasing to directly isolate the answer.
## Content
When a question contains a distinctive structural cue or partial phrase (e.g., "enthroned as the 14th..."), scan the retrieved context for identical or near-identical wording. Extract the missing term directly from this matched segment rather than synthesizing or inferring it, which minimizes hallucination and maximizes precision.

# Success Memory Item 2
## Title
Anchor-Driven Discrepancy Resolution
## Description
Use strong temporal or event-based anchors in the prompt to stabilize answers amid minor contextual variations.
## Content
If the question specifies a precise year, location, or event that clearly aligns with the context, treat it as a primary anchor. Allow this anchor to override minor peripheral inconsistencies (such as exact age or date offsets) and focus exclusively on the core entity or title linked to that confirmed point.

# Success Memory Item 3
## Title
Cross-Documenal Consistency Validation
## Description
Confirm the target answer by verifying its repeated appearance across multiple independent context snippets.
## Content
Before finalizing, quickly scan all provided documents to ensure the extracted answer appears consistently across different sources. High-frequency repetition across varied contexts signals reliability and helps filter out isolated or potentially misleading passages.
