# Failure Cause Item 1
## Title
Unjustified Answer Expansion Beyond Context Span
## Description
The agent correctly identified the entity "Rumsfeld" from the retrieved context but expanded it to "Donald Rumsfeld" based on external knowledge, causing an exact match failure against the gold answer "Rumsfeld".
## Content
The agent's reasoning explicitly acknowledged that the context contained "Rumsfeld" and considered using just that, but ultimately chose "Donald Rumsfeld" for "completeness." This decision introduced a span-boundary error: the context only supported "Rumsfeld," and the agent added information not present in the source material. The fix was to output the exact span "Rumsfeld" as provided by the context, which the judge confirmed was fully supported.

# Failure Memory Item 1
## Title
Trust the Exact Span Provided by the Context
## Description
When the retrieved context contains a direct answer span, output that span verbatim rather than expanding, modifying, or augmenting it with external knowledge.
## Content
In retrieval-based QA, the context defines the acceptable answer boundaries. If the context says "Rumsfeld," the answer is "Rumsfeld" — not "Donald Rumsfeld" or any other variation. Agents should resist the urge to normalize or complete answers unless the task instructions explicitly require it. This prevents unnecessary mismatches in exact-match evaluation.

# Failure Memory Item 2
## Title
Preserve Source Format in Structured Contexts
## Description
When answering from structured sources (e.g., Jeopardy clues with pipe-delimited answers), extract the answer token exactly as formatted in the source without transformation.
## Content
Jeopardy-style contexts use a consistent delimiter pattern (e.g., `| answer |`) where the answer field is the ground truth for that item. The agent should treat the content between delimiters as the canonical answer span. Modifying this span (adding titles, full names, etc.) breaks alignment with the source and causes evaluation failures. The generalizable lesson: when the source format is clear, respect it.

ACTION: TASK_COMPLETE
