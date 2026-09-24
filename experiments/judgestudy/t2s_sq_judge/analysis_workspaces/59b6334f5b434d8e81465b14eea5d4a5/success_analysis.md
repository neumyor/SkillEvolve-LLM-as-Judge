# Success Memory Item 1
## Title
Keyword-Guided Context Filtering
## Description
Direct document scanning using precise query terms to isolate relevant passages containing the target entity.
## Content
Map key components of the question (e.g., nationality, role, invention) to search terms. Scan retrieved texts for explicit matches linking these terms to the target subject. Prioritize sentences that directly state the relationship between the queried attributes and the entity.

# Success Memory Item 2
## Title
Multi-Source Fact Alignment
## Description
Confirm extracted facts by identifying consistent reports across multiple independent sources within the context window.
## Content
Factual retrieval often yields redundant information. Compare findings across different documents to confirm the entity or attribute is uniformly reported. Rely on consensus among sources to filter out noise, outliers, or misattributed data before finalizing the extraction.

# Success Memory Item 3
## Title
Attribute-Specific Isolation and Formatting
## Description
Extract only the exact requested field from the confirmed fact and apply strict output constraints without supplementary text.
## Content
Distinguish between the full entity and the specific attribute requested (e.g., surname vs. full name). Discard all contextual framing, explanations, or partial matches. Immediately wrap the isolated value in the required tags to satisfy structural requirements.
