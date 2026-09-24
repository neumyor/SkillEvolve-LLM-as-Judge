# Failure Cause Item 1
## Title
Span Boundary Selection Error on Title Prefix
## Description
The agent correctly identified the entity (Baden-Powell) but selected a shorter span ("Robert Baden-Powell") instead of the fuller, more precise span ("Lord Robert Baden-Powell") that appeared in the primary supporting passage.
## Content
In the first retrieved document (a Jeopardy clue), the answer is explicitly given as "Lord Robert Baden-Powell." The agent's reasoning acknowledged both variants ("Robert Baden-Powell (or Lord Robert Baden-Powell)") but committed to the shorter form without justification for dropping the title prefix. This is a span-boundary error where the agent truncated a valid, context-supported answer rather than selecting the most complete match from the source text.

# Failure Memory Item 1
## Title
Prefer Full Spans from Direct Source Passages
## Description
When extracting answers, select the span that most closely matches the explicit phrasing in the most direct or authoritative source passage, even if it includes titles or honorifics.
## Content
If a passage explicitly states "Lord Robert Baden-Powell" as the answer (as in a Jeopardy clue answer line), do not truncate it to "Robert Baden-Powell" unless the question or task constraints require it. The most faithful extraction preserves the full span as presented in the source.

# Failure Memory Item 2
## Title
Do Not Arbitrarily Drop Honorifics Without Justification
## Description
If the context provides a full title or honorific (e.g., "Lord," "Dr.") alongside the name, include it in the answer span unless the question specifically asks for just the name.
## Content
Agents should treat honorifics as part of the answer span when they appear in the source text. Dropping them requires explicit justification (e.g., the question asks for "first name only"). Absent such constraints, the complete named entity including titles is the safer, more precise extraction.

ACTION: TASK_COMPLETE
