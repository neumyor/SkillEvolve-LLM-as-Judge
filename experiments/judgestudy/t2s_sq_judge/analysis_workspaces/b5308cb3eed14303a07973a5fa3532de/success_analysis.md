# Success Memory Item 1
## Title
Isolate Core Query from Decorative Modifiers
## Description
Separate the underlying factual request from humorous, metaphorical, or pop-culture references embedded in the prompt to focus reasoning on the target variable.
## Content
When prompts attach playful clues or cultural references to a straightforward factual question, strip these decorative elements to identify the core entity and required attribute. Treat the reference as a secondary confirmation cue rather than a constraint, ensuring the model focuses on retrieving the direct factual relationship without being derailed by non-literal phrasing.

# Success Memory Item 2
## Title
Direct Relationship Mapping via Keyword Alignment
## Description
Use exact keyword matching between the core query terms and context passages to quickly locate the explicit relationship or attribute being asked.
## Content
Scan retrieved documents for the primary entity and its associated descriptor (e.g., location, classification, container). Prioritize passages that explicitly state the direct relationship using identical terminology, bypassing tangential information or unrelated quotes that share peripheral keywords but do not define the target relationship.

# Success Memory Item 3
## Minimalist Output Enforcement
## Description
Generate the final response containing only the precise requested value, formatted exactly as instructed, without adding explanations or acknowledging non-factual prompt elements.
## Content
After identifying the target fact, output only the exact term or phrase requested. Omit conversational filler, reasoning steps, or commentary on stylistic prompt features. Strictly adhere to the required tag structure to ensure clean, machine-parseable results that directly satisfy the extraction objective.
