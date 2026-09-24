# Failure Cause Item 1
## Title
Span Boundary Selection Error
## Description
The agent correctly identified the entity associated with the slogan but selected a longer span ("Hallmark Cards") instead of the shorter canonical name ("Hallmark"). This resulted in a sub-EM mismatch despite semantic correctness.
## Content
The agent's reasoning explicitly considered both "Hallmark Cards" and "Hallmark" as candidates but settled on "Hallmark Cards" because it "matches perfectly." In SearchQA, gold answers are typically the shortest unique span identifying the entity. The context supports "Hallmark" as the brand name linked to the slogan (e.g., "Hallmark Hall of Fame," "Hallmark Cards Inc."). The agent failed to apply a preference for minimal spans when multiple valid options exist.

# Failure Memory Item 1
## Title
Prefer Shortest Valid Entity Span
## Description
When multiple candidate spans identify the same entity, choose the shortest one that fully answers the question.
## Content
Many QA datasets expect the minimal span (e.g., "Hallmark" vs "Hallmark Cards"). Agents should check if a shorter variant exists in the context that still satisfies the query constraints. If so, prefer the shorter span to align with typical gold answer formats. This avoids near-miss penalties where the entity is correct but the span length differs from the gold standard.

# Failure Memory Item 2
## Title
Verify Answer Granularity Against Question Constraints
## Description
Ensure the answer length matches the expected granularity of the question by analyzing context cues.
## Content
Questions asking for a "company" might accept either the full legal name or the common brand name. However, if the context provides a clear brand association (like the slogan linked to "Hallmark"), the brand name is often the intended answer. Agents should look for cues in the question phrasing and context structure to determine whether a short or long form is appropriate, rather than defaulting to the longest available match.

ACTION: TASK_COMPLETE
