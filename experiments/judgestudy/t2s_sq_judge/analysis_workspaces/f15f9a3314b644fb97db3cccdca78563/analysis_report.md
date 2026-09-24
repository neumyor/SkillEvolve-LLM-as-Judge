# Failure Cause Item 1
## Title
Span Boundary Over-Selection: Including Descriptive Category in Entity Answer
## Description
The agent correctly identified the entity "Sirius" but included the descriptive category "Satellite Radio" in the answer span, producing "Sirius Satellite Radio" instead of the more precise "Sirius". This is a common span-boundary error where the model treats the full noun phrase as the answer rather than extracting just the core entity name.
## Content
In the retrieved context, the passage states "Curry also hosts a weekly four-hour show on Sirius Satellite Radio". The agent selected the full phrase "Sirius Satellite Radio" as the answer. However, the question asks for the "satellite radio company", and "Sirius" is the specific company name. The descriptor "Satellite Radio" is part of the company's full branding but is redundant when answering "which satellite radio company". The correct extraction should be just "Sirius", which is the minimal entity that fully answers the question without unnecessary modifiers.

# Failure Memory Item 1
## Title
Prefer Minimal Core Entity Over Full Noun Phrase
## Description
When extracting an answer span for an entity question, prefer the minimal core entity name over the full noun phrase that includes descriptive categories or modifiers. If the question already specifies the category (e.g., "satellite radio company"), the answer should be just the entity name, not the category repeated.
## Content
For questions asking "which X did Y?", if the context contains "X Z" where Z is the entity and X is the category, extract just Z. For example, "Sirius Satellite Radio" → "Sirius", "Apple Inc." → "Apple", "New York City" → "New York" (if the question asks "which city"). This avoids over-specification and aligns with how gold answers are typically formatted in QA datasets.

# Failure Memory Item 2
## Title
Verify Answer Granularity Against Question Type
## Description
Before finalizing an answer, check whether the extracted span includes information already implied by the question. If the question specifies the type of entity (company, person, place), the answer should be the specific identifier, not the type plus identifier.
## Content

ACTION: TASK_COMPLETE
