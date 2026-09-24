# Success Memory Item 1
## Title
Direct Phrase Attribution Matching
## Description
Locate exact quotes, titles, or epithets from the prompt within the retrieved context to identify the target entity.
## Content
When a query specifies a unique nickname, award, or quoted description tied to a source, scan the context for that exact string. The surrounding sentence will typically directly name the associated person or object, enabling immediate identification without requiring external knowledge or inference.

# Success Memory Item 2
## Title
Cross-Source Attribution Alignment
## Description
Confirm entity identity by verifying that multiple independent context snippets consistently link the target phrase to the same subject.
## Content
Retrieve several documents and check that the specific title or quote appears alongside the same name across different sources. High agreement between snippets eliminates ambiguity, resolves competing candidates, and establishes confidence in the selected entity before generating the final response.

# Success Memory Item 3
## Title
Constraint-Compliant Output Formatting
## Description
Isolate the identified entity to strictly adhere to required structural and length constraints.
## Content
After pinpointing the correct answer, remove all reasoning, citations, and explanatory text. Wrap only the precise entity name or value inside the designated tags to satisfy automated parsing rules and prevent formatting-related failures.
