# Success Memory Item 1
## Title
Scale-Aware Term Selection
## Description
Match the granularity of the question to the appropriate level of detail in the context.
## Content
When a prompt asks for a "part," "structure," or "component," prioritize broader anatomical or functional units over microscopic substructures. Evaluate candidates against the exact wording to ensure the selected term aligns with the expected scale (e.g., selecting "leaves" over "stomata" when the question specifies a "part of the tree").

# Success Memory Item 2
## Title
Context-Driven Candidate Filtering
## Description
Ground answer selection exclusively in explicit contextual statements while cross-referencing prompt constraints.
## Content
Extract all entities linked to the core mechanism described in the text. Discard candidates that describe processes rather than physical locations, and retain only those explicitly stated as the site of the action. Use direct statements from the context to justify the final choice before formatting.

# Success Memory Item 3
## Title
Strict Tag Encapsulation
## Description
Isolate the final answer within the designated output markers to guarantee machine readability.
## Content
Once the optimal term is identified, bypass any explanatory text or hedging. Directly output the result using the exact required syntax (e.g., `<answer>term</answer>`). This prevents parsing errors and ensures alignment with automated evaluation pipelines.
