# Failure Cause Item 1
## Title
Hallucination from External Priors vs. Retrieval Gap
## Description
The agent encountered a trivia clue where the retrieved context consisted solely of the question text without the answer. Instead of recognizing this retrieval limitation, the agent used external knowledge/associations ("watering holes" -> swimming pools) to guess "Swimming pool," which was incorrect.
## Content
The agent trusted its own semantic association over the actual ground truth ("Well"). It committed to an answer despite the context providing zero evidence for it. The correct approach in this specific retrieval failure scenario is to identify that the context is insufficient, but for the purpose of correction, the ground truth "Well" is applied.

# Failure Memory Item 1
## Title
Adjudicating Insufficient Context
## Description
When the retrieved context does not contain the answer to the question, the agent should explicitly note the retrieval limitation. Guessing based on partial keyword matches (e.g., "watering holes") leads to high-confidence errors.
## Content
Agents must distinguish between extractive QA (answer in text) and generative/trivia QA (answer not in text). If the answer is not in the text, the agent should flag the missing information rather than fabricating a span.

# Failure Memory Item 2
## Title
Trivia Clue Recognition
## Description
Recognizing the format of the input (e.g., Jeopardy clues) helps manage expectations about whether the answer is present in the snippet.
## Content
Trivia snippets often contain only the clue. Agents should be trained to handle these cases by either searching for the specific answer or acknowledging that the current context is a question-only snippet.

ACTION: TASK_COMPLETE
