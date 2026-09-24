# Success Memory Item 1
## Title
Cross-Reference Redundant Context Snippets
## Description
Confirm extracted answers by verifying consistent mentions across multiple independent retrieved documents.
## Content
When search results contain overlapping sources on a single topic, scan each snippet for the target entity. Prioritize answers that appear consistently across different documents to filter out noise, misattributions, or outlier claims before finalizing the response.

# Success Memory Item 2
## Title
Map Multi-Part Constraints to Context Keywords
## Description
Decompose questions into specific identifiers and align them with corresponding phrases in the context to isolate the precise answer.
## Content
Break down the prompt into key parameters (e.g., character name, duration, role). Search the context for exact or synonymous terms matching these parameters. Extract only the entity that simultaneously satisfies all stated constraints, ensuring contextual relevance over superficial keyword matching.

# Success Memory Item 3
## Title
Enforce Strict Output Formatting Post-Extraction
## Description
Apply the required structural template immediately upon answer confirmation, omitting all intermediate reasoning in the final output.
## Content
Once the correct entity is identified and validated, directly wrap the raw answer string in the specified tags. Avoid appending explanations, qualifiers, or conversational text to guarantee parser compatibility and adherence to system constraints.
