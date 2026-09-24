# Failure Cause Item 1
## Title
Overly Descriptive Answer Instead of Entity Name
## Description
The agent generated a descriptive phrase ("Main characters of the sitcom What's Happening!!") instead of extracting the concise entity name ("What's Happening" or "What's Happening!!") that the question implicitly requested. The question listed three character names, which is a standard SearchQA format asking for the title of the work they appear in. The agent recognized the correct show but failed to output just the title, instead providing a full sentence-like description.
## Content
The retrieved context repeatedly states "The series centered around three black teens, Roger 'Raj' Thomas, Dwayne Clemens, and Freddie 'Rerun' Stubbs" and identifies the series as "What's Happening!!". The gold answer is "What's Happening". The agent's reasoning correctly identified the show but chose to output a verbose description rather than the specific entity name. This is a span-boundary/format issue where the agent did not recognize that the expected answer is the title itself, not a description of the characters' role.

# Failure Memory Item 1
## Title
Prefer Concise Entity Names Over Descriptions
## Description
When a question lists entities (e.g., character names, people) and asks for their identity/source, the expected answer is typically the specific entity name (e.g., title of a show, book, or movie) rather than a descriptive phrase about them. Agents should extract the most concise noun phrase that directly answers the implicit "what is this?" query.
## Content
In SearchQA, questions like "[Entity1], [Entity2], [Entity3]" usually ask for the common source or category. The answer should be the shortest, most direct identifier from the context (e.g., the title), not a sentence describing the relationship. For example, if the context says "X, Y, Z are characters in Show A", the answer is "Show A", not "Characters in Show A".

# Failure Memory Item 2
## Title
Adjudicate Between Descriptive and Identifying Spans
## Description
When multiple passages provide information, agents must distinguish between descriptive context (explaining who/what something is) and identifying context (naming the entity). If the question asks for an identity, prioritize the name/title over descriptions.
## Content
The agent saw passages like "The series centered around..." and "What's Happening!! is an American sitcom...". It correctly used the former to identify the show but then constructed an answer from the descriptive language rather than extracting the title from the latter. Agents should look for the proper noun/title that serves as the canonical identifier for the group or entity in question.

ACTION: TASK_COMPLETE
