# Failure Cause Item 1
## Title
Misinterpretation of Declarative Prompt as True/False Question
## Description
The agent incorrectly assumed the prompt `"Shake It" is the last song on his 1983 album "Let's Dance"` was a True/False verification question (like BoolQ), rather than a factual query asking for the entity ("his") referred to in the statement.
## Content
The agent spent significant reasoning time debating whether to answer "True" or "Yes", ignoring that the pronoun "his" implies the question asks for the artist's name. The context clearly identifies David Bowie as the artist of the album *Let's Dance*. The correct answer is the entity "David Bowie", not a boolean value.

# Failure Memory Item 1
## Title
Handle Declarative Prompts as Entity Queries
## Description
When a prompt is a declarative sentence containing a pronoun (e.g., "his", "her", "its"), treat it as a request to identify the referent of that pronoun, not as a True/False question.
## Content
In SearchQA and similar datasets, prompts like "X is Y of Z" often ask for the missing entity (who owns Z, who made X, etc.). Agents should look for the specific entity mentioned in the context that fits the description, rather than defaulting to binary confirmation unless the dataset format explicitly supports it.

# Failure Memory Item 2
## Title
Prioritize Explicit Entity Identification Over Boolean Assumptions
## Description
Avoid assuming a True/False output format unless the question explicitly asks for verification (e.g., "Is it true that..."). Prefer extracting the specific named entity requested by the phrasing.
## Content
The agent's reasoning loop was dominated by format uncertainty ("Should I say True or Yes?"). A better approach is to parse the semantic role of each part of the prompt: "Shake It" (subject) is the last song on "his" (possessive referent needed) 1983 album "Let's Dance" (object). The context provides "David Bowie" as the artist. Extracting this entity is the robust path.

ACTION: TASK_COMPLETE
