# Success Memory Item 1
## Title
Target Entity Isolation
## Description
Explicitly parse the prompt to isolate the specific unknown variable or relationship being queried before processing retrieved context.
## Content
Identify the core missing piece of information (e.g., a person's name, title, or attribute) early in the reasoning chain. This directs the subsequent context scan toward exact keyword matches and relational phrases, preventing passive reading or distraction by peripheral details.

# Success Memory Item 2
## Title
Cross-Document Consensus Validation
## Description
Confirm factual accuracy by checking for consistent mentions of the target entity across multiple independent context snippets.
## Content
When several retrieved documents independently state the same fact or name, treat this convergence as high-confidence evidence. Prioritize answers backed by multi-source agreement to reduce extraction noise and ensure robustness against contradictory or low-quality passages.

# Success Memory Item 3
## Constraint-First Output Structuring
## Description
Apply strict formatting rules immediately upon answer identification, ensuring full compliance with required delimiters and length constraints.
## Content
Before finalizing the response, verify that the output structure exactly matches the requested format (e.g., specific tag wrappers, conciseness mandates). Omit all reasoning steps, explanations, or conversational filler to guarantee seamless parsing by automated evaluation systems.
