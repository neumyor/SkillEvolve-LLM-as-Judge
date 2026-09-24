# Failure Cause Item 1
## Title
Honorific Omission in Answer Span Extraction
## Description
The agent correctly identified the entity (Drake) but failed to include the honorific "Sir" that was explicitly present in the retrieved context, resulting in a mismatch with the expected answer format.
## Content
The agent saw passages stating "Sir Francis Drake" (e.g., [DOC] Sir Francis Drake - Angelfire, [DOC] Historic Ships) but chose to output only "Francis Drake". This is a span-selection error where the agent truncated the full named entity reference provided by the source, ignoring the honorific that was part of the canonical mention in the context.

# Failure Memory Item 1
## Title
Preserve Full Named Entity Mentions from Source Text
## Description
When extracting an answer span, always preserve the complete form of the entity as it appears in the supporting passage, including titles, honorifics, and epithets, rather than normalizing or truncating them.
## Content
If the context refers to "Sir Francis Drake", "President Lincoln", or "Dr. Smith", the extracted answer should match that full form unless the question specifically asks for just the name. Dropping honorifics or titles can cause exact-match failures even when the core entity is correct.

# Failure Memory Item 2
## Title
Prefer Explicit Full-Form Mentions Over Abbreviated References
## Description
When multiple references to the same entity exist in context (e.g., "Drake" vs "Sir Francis Drake"), prefer the fuller, more formal mention for the final answer to maximize alignment with expected answer formats.
## Content
In this case, one passage used just "DRAKE" while others used "Sir Francis Drake". The agent chose the shorter form. Generalizable lesson: when the context provides both abbreviated and full forms, default to the full form for the answer span to avoid missing critical modifiers.

ACTION: TASK_COMPLETE
