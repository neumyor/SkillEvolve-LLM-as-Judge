# Failure Cause Item 1
## Title
Confusion Between Related Architectural Terms
## Description
The agent selected "1.5 story" instead of "split-level" because it appeared more frequently in the context, despite the question being a specific definition of "split-level".
## Content
The agent observed that "1.5 story" was mentioned in many document titles and snippets, leading it to assume this was the intended answer. However, it overlooked the specific definition in the context ("Homes with a split-level entry have the entire main floor raised half a storey height") and the fact that the question phrasing is a standard dictionary definition for "split-level". The agent failed to differentiate between the broader category of "1.5 story" homes and the specific structural feature of "split-level" homes.

# Failure Memory Item 1
## Title
Prioritize Specific Definitions Over Frequent Mentions
## Description
When a question asks for a term defined by a specific phrase, prioritize passages that explicitly define that term, even if other related terms appear more often in the context.
## Content
Do not assume the most frequently mentioned term in the retrieved context is the correct answer to a definition question. Instead, scan for passages that directly link the question's phrasing or characteristics to a specific term. In this case, the agent should have noticed the passage defining "split-level" based on the "half a storey" offset, which matched the question's description more precisely than the general discussions of "1.5 story" homes.

# Failure Memory Item 2
## Title
Distinguish Interchangeable vs. Distinct Terms
## Description
Recognize that while some terms are used interchangeably in casual speech, they may have distinct meanings in technical or trivia contexts.
## Content
Even if "1.5 story" and "split-level" are often conflated in real estate discussions, a precise definition question requires identifying the exact term associated with the definition. Always check if the context provides a specific definition for one term that matches the question better than a more general term. Avoid defaulting to the more common term when a more specific one fits the definition.

ACTION: TASK_COMPLETE
