# Failure Cause Item 1
## Title
Over-specification of Answer Span due to Contextual Modifiers
## Description
The agent selected an answer span that included a contextual modifier ("Funeral") which, while semantically accurate, exceeded the brevity required by the ground truth ("Pyre").
## Content
The agent retrieved the phrase "funeral pyre" from the context and determined that "Funeral pyre" was the most complete answer to "this funeral structure". However, the ground truth is simply "Pyre". The agent failed to recognize that in this specific Jeopardy-style query, the core noun alone is the expected answer, leading to a partial match failure (F1: 0.67) rather than a full match.

# Failure Memory Item 1
## Title
Prefer Concise Core Nouns for "Structure" or "Entity" Questions
## Description
When answering questions about structures or entities described with modifiers (e.g., "funeral structure"), prefer the single core noun (e.g., "pyre") over the full compound phrase (e.g., "funeral pyre") unless the modifier is essential to distinguish the entity.
## Content
In many trivia and Jeopardy contexts, the answer key expects the shortest unique identifier. If the context contains "X Y" and the question asks for "Y-like structure", check if "Y" alone is sufficient. Over-including adjectives often leads to EM/F1 penalties.

# Failure Memory Item 2
## Title
Adjudicating Between Synonymous Phrases
## Description
When multiple synonymous phrases exist in the context (e.g., "funeral boat" vs "funeral pyre"), prioritize the one that matches the specific terminology used in the definition or the most direct structural description.
## Content
The context mentioned both "funeral boat" and "funeral pyre". The agent correctly leaned towards "pyre" as a "structure" but added "funeral". Future agents should note that "pyre" is the distinct term for the burning structure, whereas "boat" is the vessel. When choosing between "Boat" and "Pyre", "Pyre" is the functional answer for the burning event, but "Pyre" is the precise lexical match for the gold answer.

ACTION: TASK_COMPLETE
