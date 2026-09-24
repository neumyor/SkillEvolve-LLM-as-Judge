# Success Memory Item 1
## Title
Constraint-Driven Entity Matching
## Description
Map explicit question constraints directly to context candidates to verify a precise match.
## Content
Decompose the prompt into verifiable criteria (e.g., temporal markers, geographic descriptors, specific outcomes) and cross-reference them against retrieved documents. Confirm the entity satisfies every condition before proceeding.

# Success Memory Item 2
## Title
Minimalist Answer Extraction
## Description
Isolate the exact entity requested, removing all surrounding context or explanatory phrasing.
## Content
Once the matching entity is confirmed, extract only the precise term or phrase that answers the question. Avoid paraphrasing, summarizing, or appending additional facts to preserve accuracy and reduce noise.

# Success Memory Item 3
## Title
Strict Format Adherence
## Description
Enclose the isolated answer in the specified delimiters without deviation or extra text.
## Content
Immediately wrap the extracted entity in the required output structure (e.g., XML tags). Perform a final check to ensure no reasoning steps, conversational filler, or metadata leak outside the designated answer block.
