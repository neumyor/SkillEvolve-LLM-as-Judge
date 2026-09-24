# Failure Cause Item 1
## Title
Span Expansion Error: Agent Expanded Explicit Answer Span

## Description
The agent correctly identified the target entity but expanded the answer span beyond what the context explicitly provided, converting "Clark" to "Wesley Clark".

## Content
The first passage (Jeopardy format) explicitly states the answer as "Clark." — this is the most direct source. The agent also found corroborating evidence in the Wesley Clark passage but chose to output the expanded form "Wesley Clark" instead of the exact span "Clark" given in the primary answer source. This is a span-boundary error: the agent added the first name even though the context's authoritative answer field contained only the last name. The F1 score of 0.667 reflects partial overlap (both contain "Clark") but EM=0.0 confirms the exact string did not match. The fix was to use the minimal span "Clark" as explicitly stated in the Jeopardy passage.

# Failure Memory Item 1
## Title
Trust Explicit Answer Spans Over Inferred Expansions

## Description
When a retrieved passage explicitly provides an answer (e.g., Jeopardy Q&A format, direct statement), use that exact span rather than expanding it with inferred full names or additional qualifiers.

## Content
In SearchQA tasks, some passages are structured as direct question-answer pairs (like Jeopardy clues). When such a passage gives an answer like "Clark.", do not expand it to "Wesley Clark" unless the task context explicitly requires the full name. The correct approach is to extract the answer span exactly as presented in the most authoritative source passage. This applies to any task where the answer may be a last name, abbreviation, or partial entity reference.

# Failure Memory Item 2
## Title
Prioritize Direct Answer Sources Over Corroborating Context

## Description
When multiple passages support the same entity, prefer the passage that directly answers the question over those that merely corroborate or provide background.

## Content
The agent used the Wesley Clark passage to confirm its answer choice but should have recognized that the Jeopardy passage was the direct answer source. In general, when one passage contains a direct answer (Q→A mapping) and another provides supporting details, the direct answer span takes precedence. Use corroborating passages only to verify correctness, not to construct or expand the answer itself.

ACTION: TASK_COMPLETE
