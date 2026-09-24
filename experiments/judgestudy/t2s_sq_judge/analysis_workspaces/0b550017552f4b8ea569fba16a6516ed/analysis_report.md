# Failure Cause Item 1
## Title
Overreliance on External Knowledge Instead of Context Extraction
## Description
The agent ignored the direct contextual evidence pointing to the correct answer and instead used external knowledge to guess an incorrect term.
## Content
The retrieved context included a Jeopardy-style clue mentioning "shanty-town" in connection with poor people living in shacks. The agent recognized the clue structure but failed to extract "shanty" from "shanty-town". Instead, it guessed "Boozer" based on its own knowledge base, despite the context providing a stronger signal via the compound term.

# Failure Memory Item 1
## Title
Extract Answers Directly from Contextual Phrases
## Description
When the retrieved context contains phrases that semantically match the question's clues, extract the relevant span directly rather than substituting external knowledge.
## Content
In trivia/extraction tasks, if the context mentions a compound term like "shanty-town" alongside descriptors matching the question (e.g., "poor people may live in a town of them"), the component word "shanty" is likely the intended answer. Always prioritize explicit contextual signals over inferred or memorized answers.

# Failure Memory Item 2
## Title
Validate Candidate Answers Against All Retrieved Documents
## Description
Before committing to an answer, verify that the candidate is supported by at least one passage in the retrieved context, especially when the context contains the exact question phrasing.
## Content
The first document in the context contained the exact question text. If the agent had checked whether any passage supported "Boozer" versus "shanty", it would have found "shanty-town" as a supporting phrase. Agents should cross-reference their chosen answer against all provided documents to ensure contextual support exists.

ACTION: TASK_COMPLETE
