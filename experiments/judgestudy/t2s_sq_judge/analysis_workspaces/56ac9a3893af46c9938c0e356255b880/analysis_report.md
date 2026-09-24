# Failure Cause Item 1
## Title
Span Selection Error: Full Title vs. Partial Entity
## Description
The agent selected the full title "The Outcasts of Poker Flat" as the answer, whereas the correct answer is the shorter span "The Outcasts".
## Content
The question "Bret Harte wrote about these exiles 'of Poker Flat'" is structured as a fill-in-the-blank or entity identification task targeting the specific word(s) preceding "of Poker Flat" in the title. The agent interpreted the question as asking for the name of the work entirely, leading to the selection of the full string "The Outcasts of Poker Flat". While semantically related, this is a span-boundary error; the correct answer is just "The Outcasts", which completes the phrase implied by the question. The agent should have recognized that the question provides the suffix "'of Poker Flat'" and requested the prefix or the core entity "The Outcasts".

# Failure Memory Item 1
## Title
Question Structure Analysis for Partial Titles
## Description
When a question includes a known part of a title (e.g., "... 'of Poker Flat'"), the expected answer is often the missing part or the core entity, not the full title.
## Content
In QA datasets, questions like "X wrote about Y 'of Z'" often expect the answer to be the specific term Y that completes the proper noun or title. Agents should parse the question to identify what information is already provided in the prompt versus what is being asked. If the prompt contains a significant portion of the likely answer (like the end of a title), the model should look for the corresponding beginning or the distinct entity name, rather than outputting the entire known phrase.

# Failure Memory Item 2
## Description
Sub-EM Score Indicates Containment, Not Exact Match
## Content
A Sub-EM score of 1.0 indicates that the gold answer is a substring of the predicted answer. This signals a span-boundary issue rather than a retrieval or hallucination failure. When diagnosing such failures, focus on whether the agent included extra words that were not required by the strict answer format, rather than questioning the relevance of the retrieved context.

ACTION: TASK_COMPLETE
