# Failure Cause Item 1
## Title
Misinterpreting definitional questions as requesting specific examples rather than general categories
## Description
When the question uses a definitional format like "An [category] applied [location] to [purpose]", the expected answer is often the general term for that category, not a specific instance mentioned in the context.
## Content
The question "An astringent applied under the arms to curtail sweating" asks for the general class of substance. The agent identified specific examples from the context (witch hazel, apple cider vinegar) and selected one based on frequency of mention, missing that the question seeks the umbrella term "anti-perspirant". The context contains a passage explicitly titled "About Antiperspirants" stating "Antiperspirants reduce underarm sweating", which directly answers the question. The agent should have recognized the definitional structure of the question and looked for the general category term rather than latching onto the most frequently mentioned specific example.

# Failure Memory Item 1
## Title
Prioritize question format over entity frequency when selecting answer spans
## Description
Definitional or fill-in-the-blank style questions ("An X that does Y") typically expect the general category name, not a specific instance. Frequency of mention in context should not override this structural cue.
## Content
When encountering questions phrased as definitions or descriptions of a category, first determine whether the question asks for the category name itself or a specific example. If the question reads like a dictionary definition or crossword clue, the answer is likely the general term. Scan the context for passages that define or name the category directly, rather than just counting which specific entity appears most often. In this case, the agent should have noticed the "About Antiperspirants" passage and recognized it as the direct answer to a definitional question about substances that reduce underarm sweating.

# Failure Memory Item 2
## Title
Consider all candidate entities including those in less prominent passages
## Description
Agents should evaluate all relevant passages in the retrieved context, not just the ones where the target entity appears most frequently. Less prominent but semantically precise passages may contain the correct answer.
## Content
The agent focused heavily on passages mentioning witch hazel (which appeared in multiple documents) while giving insufficient attention to the "About Antiperspirants" passage that directly addresses the question's concept. When multiple candidates exist, compare them against the question's semantic requirements: does the question ask for a specific brand/example or a general category? The presence of a dedicated passage about antiperspirants discussing their function should have triggered consideration of that term as a potential answer, regardless of its lower mention count compared to witch hazel.

ACTION: TASK_COMPLETE
