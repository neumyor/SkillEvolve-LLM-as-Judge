# Failure Cause Item 1
## Title
Over-specification of Answer Span
## Description
The agent selected a longer, more detailed version of the correct entity ("Jean-Honoré Fragonard") instead of the concise form ("Fragonard") that the context and question format support, causing an exact-match failure despite identifying the correct person.
## Content
The retrieved context explicitly uses "Fragonard" as a standalone reference (e.g., "The Swing by Fragonard in the Rococo period") and "Jean Honore Fragonard" as the full name. The question includes "(VIDEO DAILY DOUBLE)", a Jeopardy-style marker that conventionally expects the surname or last name as the answer. The agent unnecessarily expanded the answer to include first names and diacritics, committing to a more specific form than the context or question format required. This produced an EM of 0.0 even though the F1 score was 0.67 and sub_EM was 1.0, confirming the entity was correct but the span was too long.

# Failure Memory Item 1
## Title
Prefer Concise Entity Forms When Context Supports Them
## Description
When multiple forms of an entity appear in context (e.g., full name vs. surname), prefer the shortest unambiguous form that matches the question's expected granularity.
## Content
In trivia and Jeopardy-style questions, answers are often expected as surnames or single terms rather than full names. Check whether the context uses a shorter form prominently, and whether the question format implies a particular level of specificity. Avoid adding diacritics, middle names, or honorifics unless explicitly required by the context or question. When the context contains both "Fragonard" and "Jean Honore Fragonard", the shorter form is sufficient and often preferred for exact-match evaluation.

# Failure Memory Item 2
## Title
Align Answer Granularity with Question Format Cues
## Description
Questions with format markers like "(VIDEO DAILY DOUBLE)" signal Jeopardy-style responses, which conventionally use surnames or short identifiers.
## Content: Recognize meta-cues in the question text that indicate the expected answer format. Jeopardy clues typically expect the respondent's name as a surname only. Adjust your answer extraction accordingly to match this convention rather than defaulting to the most complete name form found in context. When the context provides both a full name and a surname reference, the surname alone is usually the intended answer for such formats.

ACTION: TASK_COMPLETE
