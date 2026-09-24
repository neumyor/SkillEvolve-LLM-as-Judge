# Success Memory Item 1
## Title
Multi-Source Entity Correlation
## Description
Leverage overlapping keywords across multiple retrieved documents to confirm relationships between prompt entities.
## Content
When a query combines a specific person, event, and metric, scan all available context snippets for intersecting terms. Consistent co-occurrence of these keywords across independent sources strongly indicates the correct semantic link, allowing the model to triangulate the answer even when individual passages contain fragmented information.

# Success Memory Item 2
## Title
Statistic-Driven Entity Resolution
## Description
Use unique numerical or performance metrics as primary anchors to locate the target entity.
## Content
Highly specific statistics (e.g., exact completion percentages, scores, or dates) act as reliable filters within retrieved text. Match these values directly to the surrounding narrative to isolate the exact paragraph containing the answer, bypassing irrelevant biographical or historical details that may clutter the context window.

# Success Memory Item 3
## Title
Canonical Name Extraction
## Description
Prioritize full, formal entity names over abbreviations when formulating the final answer.
## Content
Context often contains both shortened references (e.g., "Giants") and full designations (e.g., "New York Giants"). Extract the complete, formally recognized name present in the supporting text to ensure clarity and alignment with standard answer formats, avoiding ambiguity that could arise from truncated identifiers.
