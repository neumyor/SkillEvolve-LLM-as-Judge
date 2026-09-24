# Failure Cause Item 1
## Title
Span Over-Generation: Appending Descriptor Not in Context Span

## Description
The agent correctly identified the target entity (Amazon) but over-generated the answer span by appending "River", producing "Amazon River" instead of the context-supported minimal span "Amazon" (gold: "the Amazon"). This caused an exact-match (EM) failure despite semantic correctness (sub_EM=1.0).

## Content
The retrieved context from the StudyStack flashcard explicitly states "ITS UPPER BRANCH IS THE MARANON, THE LOWER BRANCH THE UCAYALI; BOTH FLOW IN PERU, AMAZON." — the word "AMAZON" appears as a standalone token without "River". The agent's reasoning correctly noted this but then chose to add "River" based on general knowledge rather than selecting the minimal span present in the context. The decision to normalize to "Amazon River" instead of accepting "Amazon" as sufficient was the causal error. The context fully supports "Amazon" as the answer; no additional descriptor is needed or present in the supporting passage.

# Failure Memory Item 1
## Title
Prefer Minimal Context-Supported Spans Over Descriptive Normalization

## Description
When selecting an answer span, prefer the shortest span directly present in the supporting context over adding descriptive suffixes (e.g., "River", "City", "Country") that are not part of the extracted text.

## Content
In SearchQA-style tasks, exact-match scoring penalizes extra words even when the core entity is correct. If the context says "AMAZON" and the question asks for a river name, "Amazon" is the faithful extraction. Adding "River" reflects external knowledge normalization rather than context-grounded span selection. Agents should extract the minimal contiguous span that answers the question, resisting the urge to make answers "sound more complete."

# Failure Memory Item 2
## Title
Diagnose Near-Miss Failures as Span-Boundary Errors, Not Entity Errors

## Description
When EM=0 but sub_EM=1.0 (or high F1), the agent likely selected the correct entity but with incorrect span boundaries — either too long (extra words appended) or too short (missing required words).

## Content
A near-miss pattern (correct entity, wrong string) is usually a span-boundary problem, not a retrieval or entity-recognition failure. The agent found the right passage and identified the right concept. The fix is narrower: trim the answer to the minimal context-supported span. This diagnostic heuristic helps distinguish between agents that need better retrieval vs. agents that need tighter span selection discipline.

ACTION: TASK_COMPLETE
