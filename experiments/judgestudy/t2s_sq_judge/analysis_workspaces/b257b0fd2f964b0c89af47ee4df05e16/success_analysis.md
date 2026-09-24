# Success Memory Item 1
## Title
Anchor-Based Entity Resolution
## Description
Leverage explicit identifiers in the prompt (names, titles, dates) as direct lookup keys within retrieved context to isolate the target entity efficiently.
## Content
When a query contains specific anchors such as a relative’s name, a publication title, or a year, treat these as exact search parameters rather than open-ended clues. Scan the retrieved snippets for overlapping mentions of these anchors. The intersection of these identifiers in a single document typically yields the precise answer, eliminating the need for complex reasoning or external knowledge retrieval.

# Success Memory Item 2
## Title
Constraint-Aligned Output Formatting
## Description
Enforce strict adherence to structural output requirements by isolating the final answer and applying the mandated tags immediately upon confirmation.
## Content
Factual accuracy alone is insufficient if the response fails parsing rules. Once the target entity is confirmed via context matching, strip away explanatory text or conversational framing. Directly wrap the extracted string in the specified delimiters (e.g., `<answer>...</answer>`). This practice guarantees compatibility with automated grading systems and downstream pipelines that rely on rigid format expectations.

# Success Memory Item 3
## Title
Multi-Factor Context Intersection
## Description
Validate candidate answers by confirming they simultaneously satisfy all distinct constraints presented in the original prompt.
## Content
Before finalizing a response, cross-check the proposed answer against every specific detail in the question (e.g., familial relationship, creative work, release timeframe). If multiple documents surface, prioritize the one that explicitly links all constraints together. This intersection method reduces ambiguity, prevents partial matches from being selected, and ensures the extracted entity fully satisfies the query’s composite conditions.
