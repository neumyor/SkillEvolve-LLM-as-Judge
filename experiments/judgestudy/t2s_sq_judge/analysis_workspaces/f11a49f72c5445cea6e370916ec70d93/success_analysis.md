# Success Memory Item 1
## Title
Constraint Decomposition & Context Matching
## Description
Systematically break down the prompt into discrete entities and attributes to guide precise information extraction from the retrieved context.
## Content
Parse the question to isolate key constraints (e.g., creator, year, award, category). Cross-reference each constraint against the provided documents to filter candidates, ensuring every condition is met before finalizing the response. This reduces ambiguity and prevents misattribution.

# Success Memory Item 2
## Title
Clue-Driven Candidate Validation
## Description
Leverage distinctive partial phrases or quoted hints in the question to rapidly confirm or reject potential answers found in the context.
## Content
When a prompt includes a unique identifier or fragment (e.g., a specific word in quotes), actively scan the context for exact or near-exact matches containing that string. This technique accelerates confirmation and acts as a built-in consistency check against similar but incorrect options.

# Success Memory Item 3
## Title
Strict Delimiter Enforcement
## Description
Isolate the final extracted answer within the requested structural tags, separating it cleanly from reasoning text.
## Content: After logical deduction, place only the direct answer inside the specified markers (e.g., `<answer>...</answer>`). Avoid embedding explanations, qualifiers, or trailing punctuation within the tags to ensure parseability and alignment with automated evaluation standards.
