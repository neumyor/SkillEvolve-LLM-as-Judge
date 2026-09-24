# Failure Cause Item 1
## Title
Overly Specific Answer Span Selection
## Description
The agent correctly identified the target entity but selected a longer name variant ("Napoleon Bonaparte") than what the context and question format supported ("Napoleon").
## Content
The agent's reasoning correctly traced the pronoun "his" to Napoleon, but it committed to the full name "Napoleon Bonaparte" instead of the shorter "Napoleon" used in the gold answer. Multiple passages in the retrieved context refer to the figure simply as "Napoleon," and the Jeopardy-style question format typically expects the shortest, most direct entity reference. The agent should have preferred the minimal span that uniquely identifies the entity, especially when the context consistently uses the shorter form.

# Failure Memory Item 1
## Title
Prefer Minimal Unique Entity Spans
## Description
When multiple name variants for the same entity appear in context, select the shortest form that unambiguously identifies the target.
## Content
In QA tasks, especially those derived from trivia or Jeopardy formats, the expected answer often matches the most concise entity reference used throughout the supporting documents. Agents should scan all passages for the most frequently used short form and prefer it over longer full-name variants unless the question explicitly requires the full name. This reduces unnecessary verbosity and aligns with typical gold-answer granularity.

# Failure Memory Item 2
## Title
Align Answer Granularity with Question Style
## Description
Match the expected answer length and specificity to the style of the question being answered.
## Content
Jeopardy-style prompts, cloze deletions, and fill-in-the-blank questions typically expect single-entity, short-form answers rather than elaborated names or phrases. Agents should recognize question format cues and adjust their answer span selection accordingly, favoring brevity and directness when the question structure implies a simple entity lookup. This ensures the output matches the expected level of detail.

ACTION: TASK_COMPLETE
