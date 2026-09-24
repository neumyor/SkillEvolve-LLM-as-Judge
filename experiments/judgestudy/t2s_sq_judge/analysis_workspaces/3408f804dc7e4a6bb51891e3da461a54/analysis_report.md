# Failure Cause Item 1
## Title
Over-comprehensive answer selection instead of prioritizing the primary source
## Description
The agent identified all animals mentioned across multiple passages (sheep, goats, cattle, hogs, horses, mules, donkeys, kangaroo, water buffalo) and listed them all, failing to recognize that the question expects the most common/primary source.
## Content
The retrieved context repeatedly emphasizes sheep as the primary source ("particularly sheep", "especially sheep", "usually use sheep or goat intestines"). The agent treated the question as requesting an exhaustive enumeration rather than the definitive answer. This is a span-selection error where the agent failed to apply relevance filtering based on frequency and emphasis markers in the text.

# Failure Memory Item 1
## Title
Prioritize emphasized primary sources over exhaustive lists
## Description
When a question asks for a source or origin and the context highlights one entity with emphasis words like "particularly," "especially," or "usually," select that entity as the answer rather than listing all mentioned possibilities.
## Content
SearchQA questions often expect the most representative or common answer. Contexts may mention multiple candidates, but the correct answer is typically the one most frequently cited or explicitly marked as primary. Agents should look for linguistic cues indicating prominence and prefer concise, focused answers over comprehensive enumerations.

# Failure Memory Item 2
## Title
Match answer granularity to question expectations
## Description
Questions phrased as "X comes from these animals" or similar singular/plural forms often expect a single entity or short phrase, not a long list. Agents should calibrate answer length to what the question structure implies.
## Content
The agent produced a 9-item list when the gold answer was a single word. In many SearchQA items, even when multiple valid answers exist, the expected output is the most salient one. Agents should default to concise answers and only expand if the question explicitly requests all options or uses language like "list all."

ACTION: TASK_COMPLETE
