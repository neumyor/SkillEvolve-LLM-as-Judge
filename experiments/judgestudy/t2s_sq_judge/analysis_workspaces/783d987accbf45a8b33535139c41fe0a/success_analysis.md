# Success Memory Item 1
## Title
Entity Mapping via Cross-Snippet Verification
## Description
Align question components with context fragments and use multiple corroborating references to isolate the correct target entity.
## Content
Decompose the query into core identifiers (e.g., timeframe, organization, relationship). Scan retrieved documents for overlapping mentions of these identifiers. When multiple independent snippets consistently point to the same entity, treat it as confirmed and extract it directly without adding external knowledge.

# Success Memory Item 2
## Title
Constraint-Driven Output Formatting
## Description
Validate the extracted answer against explicit structural instructions before generation.
## Content
After isolating the answer span, immediately check the prompt for mandatory formatting rules (e.g., specific tags, delimiters, or length constraints). Wrap or adjust the extracted text to strictly match the requested template, ensuring no conversational filler or unrequested analysis appears in the final output.

# Success Memory Item 3
## Title
Focused Evidence-to-Answer Chain
## Description
Maintain a tight reasoning loop that directly links query elements to context evidence.
## Content
Structure internal processing as: restate objective → cite matching context lines → state extracted answer → verify format compliance. Suppress the urge to summarize broader context or explain peripheral details; keep the cognitive path strictly linear and optimized for direct answer retrieval.
