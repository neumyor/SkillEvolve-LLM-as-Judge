# Failure Cause Item 1
## Title
Span Selection Error - Overly Specific Title Choice
## Description
The agent correctly identified the target entity but selected an unnecessarily long title span when a shorter, equally valid span appeared in the context.
## Content
The agent's reasoning correctly matched Matthew Perry and Bradley Whitford to the show described as a behind-the-scenes sketch-comedy series. However, it committed to the full title "Studio 60 on the Sunset Strip" despite multiple passages in the retrieved context referring to the show simply as "Studio 60" (e.g., TMZ.com passage: '"Studio 60" stars Matthew Perry, Bradley Whitford and Amanda Peet'; Futon passage: 'legendary sketch comedy series "Studio 60"'). The agent did not consider that the shorter span was sufficient and aligned with the gold answer. This is a span-boundary problem: the agent included extraneous qualifiers ("on the Sunset Strip") when the core entity name alone was adequate.

# Failure Memory Item 1
## Title
Prefer Shortest Unambiguous Span
## Description
When multiple valid text spans identify the same entity, select the shortest one that is unambiguous in context.
## Content
In QA tasks, gold answers often use canonical or short forms rather than full titles with qualifiers. When the context supports both a short and long form (e.g., "Studio 60" vs. "Studio 60 on the Sunset Strip"), prefer the shorter span unless the question specifically requires the full title. This reduces over-specification errors and aligns with typical gold answer granularity.

# Failure Memory Item 2
## Title
Verify Span Against All Context Passages
## Description
Before committing to an answer span, scan all relevant passages for alternative phrasings of the same entity.
## Content
The agent only considered three passages in its reasoning but ignored others that used shorter references. A robust strategy is to collect all mentions of the candidate entity across passages and choose the most common or simplest form. This prevents bias toward the first or most detailed mention and increases alignment with gold answers that may use different phrasing.

ACTION: TASK_COMPLETE
