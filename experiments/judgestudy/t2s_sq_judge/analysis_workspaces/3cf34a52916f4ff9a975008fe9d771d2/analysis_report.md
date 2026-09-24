# Failure Cause Item 1
## Title
Span Selection and Normalization Mismatch (Singular vs Plural)
## Description
The agent correctly identified the target entity (strawberry) but selected the singular, capitalized form "Strawberry" from the festival name rather than the plural, lowercase form "strawberries" present elsewhere in the context. This resulted in a strict string match failure despite correct semantic understanding.
## Content
The retrieved context contains multiple references to the fruit, including the proper noun phrase "Strawberry Festival" and the common noun "strawberries" (e.g., "million strawberries"). The agent anchored its answer to the capitalized singular form in the event title. In SearchQA tasks, the expected answer often matches a specific span in the text verbatim. When both singular and plural variants exist, the model should prefer the exact span that aligns with the gold answer's morphology or default to the most direct noun phrase answering "this fruit" without unnecessary capitalization.

# Failure Memory Item 1
## Title
Prefer Verbatim Context Spans Over Derived Forms
## Description
When extracting answers, prioritize exact substrings from the context over normalized or derived variations (e.g., singular vs. plural, title case vs. lowercase).
## Content
SearchQA evaluation typically uses exact string matching or very tight fuzzy matching. If the context contains "strawberries" and the gold answer is "strawberries", selecting "Strawberry" from "Strawberry Festival" will fail. Always scan for the exact word form requested by the question syntax and match it directly in the text before applying grammatical transformations.

# Failure Memory Item 2
## Title
Case Sensitivity in Answer Extraction
## Description
Avoid automatically capitalizing extracted answers unless they are proper nouns at the start of a sentence or explicitly required by the question format.
## Content
The agent capitalized "Strawberry" likely due to its appearance in the title "Strawberry Festival". However, the gold answer "strawberries" is lowercase. For generic entity answers, preserve the casing as it appears in the supporting span or use lowercase unless the entity is inherently capitalized. Do not assume title-case extraction is preferred.

ACTION: TASK_COMPLETE
