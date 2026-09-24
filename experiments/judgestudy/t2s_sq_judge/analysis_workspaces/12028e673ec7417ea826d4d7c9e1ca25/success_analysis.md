# Success Memory Item 1
## Title
Query Constraint Extraction
## Description
Isolate explicit factual markers from the prompt to serve as precise search anchors within the retrieved context.
## Content
Parse the question for unique identifiers such as birth years, relational milestones, specific names, titles, or numerical thresholds. Use these extracted constraints to systematically filter candidate entities in the provided documents, ensuring each stated criterion is explicitly satisfied before considering a match valid.

# Success Memory Item 2
## Title
Contextual Consensus Prioritization
## Description
Resolve minor contextual discrepancies by relying on strong cross-document agreement for the core entity.
## Content: When retrieved passages contain slight variations in peripheral details (e.g., differing counts of years, dates, or secondary facts), prioritize the entity that consistently satisfies the primary identifying conditions across multiple independent sources. Treat minor numerical or phrasing mismatches as noise if the central identification remains unambiguous and widely corroborated.

# Success Memory Item 3
## Title
Strict Output Formatting
## Description
Adhere precisely to the required response structure to ensure compatibility with automated evaluation pipelines.
## Content
Generate the final answer using only the necessary identifier or phrase, enclosed strictly within the designated XML-style tags. Omit introductory phrases, reasoning steps, or explanatory text in the final output block to prevent parsing failures, token waste, or metric penalties.
