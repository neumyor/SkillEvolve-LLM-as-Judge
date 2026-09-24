# Failure Cause Item 1
## Title
Misinterpretation of Entity Query as Description Request
## Description
The agent failed to recognize that a question consisting only of an entity name and year ("Rachel, Rachel"(1968)) in this dataset format typically asks for a specific key attribute (e.g., director), not a general summary.
## Content
The agent's reasoning explicitly considered that the prompt "might be looking for a specific fact" but defaulted to generating a descriptive sentence because it perceived the query as open-ended. It extracted the correct information (Paul Newman) but wrapped it in a verbose sentence instead of isolating the target entity span. This indicates a failure to map the implicit question type (Who directed?) to the expected concise answer format.

# Failure Memory Item 1
## Title
Prefer Concise Entity Spans for Single-Entity Gold Answers
## Description
When the gold answer is a single entity (name, date, etc.), the agent should extract that specific span rather than generating a descriptive sentence containing it.
## Content
In SearchQA-style tasks, questions like "Entity(Year)" often imply "What is the [key attribute] of Entity?". If the context supports a specific entity answer, output just that entity. Avoid adding context like "A film directed by..." unless the question explicitly asks for a description. The instruction "typically a few words or a short phrase" reinforces this preference for brevity and precision.

# Failure Memory Item 2
## Title
Adjudicate Open-Ended Queries by Contextual Clues
## Description
When a query is ambiguous (e.g., just a title), use the retrieved context's most prominent facts and the task's typical patterns to infer the likely intent.
## Content
If multiple facts are available (director, star, plot), look for cues. In this case, the repeated emphasis on Paul Newman as director across multiple documents, combined with the single-entity gold answer structure, should signal that "director" is the intended target. The agent should prioritize extracting the most salient single-entity fact over synthesizing a multi-fact summary.

ACTION: TASK_COMPLETE
