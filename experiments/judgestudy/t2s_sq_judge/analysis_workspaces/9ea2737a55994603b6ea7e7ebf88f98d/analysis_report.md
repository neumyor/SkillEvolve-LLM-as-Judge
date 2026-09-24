# Failure Cause Item 1
## Title
Over-Specific Answer Selection Despite Context Supporting Simpler Span
## Description
The agent identified the correct entity (falcon) but selected a more specific compound noun phrase ("Maltese Falcon") instead of the simpler, context-supported span ("a falcon") that matched the question's phrasing ("1 of these birds").
## Content
The retrieved context contains multiple references to the rent being paid in the form of "a falcon" or "one single Maltese Falcon." The agent correctly reasoned that the bird was a falcon but committed to the more specific "Maltese Falcon" as the final answer. While factually related, the question asks for "1 of these birds," and the context explicitly phrases the answer as "a falcon" in several places (e.g., Passage 7: "a falcon..."). The agent failed to recognize that the simpler span was the intended target, leading to an exact match failure despite semantic correctness.

# Failure Memory Item 1
## Title
Match Answer Granularity to Question Phrasing
## Description
When the question asks for "1 of these [entity type]," prefer the simplest noun phrase directly answering the query over more specific or compound variants, unless the context exclusively uses the specific variant.
## Content
In trivia-style QA, questions often use generic prompts like "1 of these birds" or "what animal." The expected answer is usually the base entity name (e.g., "falcon") rather than a specific subtype or proper noun phrase (e.g., "Maltese Falcon") unless the context strongly implies otherwise. Agents should check if the context supports the simpler span and align with the question's level of abstraction.

# Failure Memory Item 2
## Title
Prioritize Explicit Direct Mentions Over Inferred Specificity
## Description
If the context explicitly states a simple term (e.g., "a falcon") alongside a more specific one (e.g., "Maltese Falcon"), and the question is open-ended, default to the explicit simple term as the primary answer span.
## Content
Agents should scan for direct answers to the question's core query. When multiple valid spans exist, the one that most directly matches the question's syntactic structure and simplicity should be chosen. Over-specification can lead to exact match failures even when the semantic content is correct.

ACTION: TASK_COMPLETE
