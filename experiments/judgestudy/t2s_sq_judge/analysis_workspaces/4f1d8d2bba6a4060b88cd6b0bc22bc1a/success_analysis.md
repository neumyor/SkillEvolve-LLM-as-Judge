# Success Memory Item 1
## Title
Constraint-Driven Context Anchoring
## Description
Extract explicit factual markers from the query to directly locate matching information within retrieved snippets.
## Content
Parse the question for unique identifiers (e.g., specific awards, years, event counts) and scan the context exclusively for sentences containing those markers. This narrows the search space and reduces evaluation overhead when processing multiple documents.

# Success Memory Item 2
## Title
Multi-Signal Entity Resolution
## Description
Use overlapping details across different sources to confidently identify the target entity.
## Content
When snippets reference the same event or achievement with slightly varying phrasing, align the shared attributes (e.g., Olympic year, medal tally, award title) to isolate the correct subject. Prioritize consensus across documents over isolated mentions to strengthen confidence in the selection.

# Success Memory Item 3
## Title
Structural Compliance Enforcement
## Description
Validate and enforce output formatting rules before finalizing the response.
## Content
Before generating the final output, explicitly check against all structural constraints (e.g., required tags, length limits, tone). Strip away intermediate reasoning or conversational filler to deliver only the precisely formatted answer.
