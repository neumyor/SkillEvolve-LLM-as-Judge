# Success Memory Item 1
## Title
Prioritize Verbatim Snippet Overlaps
## Description
For trivia and factoid queries, immediately scan retrieved contexts for exact phrase matches with the prompt, as they frequently contain direct answers or highly targeted clues.
## Content
When a retrieved document reproduces the question's wording or uses it as a quiz clue, extract the corresponding answer directly from that same passage. Treat verbatim alignment as a high-confidence signal before searching further.

# Success Memory Item 2
## Title
Cross-Reference Core Identifiers
## Description
Confirm candidate answers by checking that all explicit constraints in the question (e.g., year, medium, author, premise) align consistently across independent reference sources.
## Content
After locating a potential match, quickly consult authoritative entries like encyclopedias or databases to ensure every detail in the prompt corresponds to the candidate. Proceed only when multi-source attribute alignment is complete.

# Success Memory Item 3
## Title
Isolate Canonical Entity for Output
## Description
Once the correct subject is identified, strip away modifiers, years, or descriptive phrases and output only the core entity name inside the required tags.
## Content
Avoid appending release dates, alternate titles, or explanatory notes. Reduce the final response to the most concise, standardized form of the answer and wrap it strictly in the specified formatting markers to satisfy automated grading.
