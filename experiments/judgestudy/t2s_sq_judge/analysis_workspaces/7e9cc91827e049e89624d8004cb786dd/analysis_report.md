# Failure Cause Item 1
## Title
Span Boundary Over-selection
## Description
The agent correctly identified the relevant entity but selected the full phrase "Roanoke Island" instead of the canonical answer "Roanoke".
## Content
The agent's internal monologue explicitly weighed "Roanoke" against "Roanoke Island" and chose the latter for perceived precision. However, the gold answer is "Roanoke". The agent failed to realize that the root entity name is the expected output format, leading to an exact match failure despite semantic correctness.

# Failure Memory Item 1
## Title
Minimal Span Extraction Preference
## Description
Prefer the shortest valid span that names the entity over longer descriptive phrases.
## Content
When the context contains "Entity Name + Descriptor" (e.g., Roanoke Island), and the question asks for the entity, the answer is often just the "Entity Name". Agents should avoid adding descriptors unless necessary for disambiguation.

# Failure Memory Item 2
## Title
Self-Correction on Redundancy
## Description
Do not discard shorter, simpler answers in self-verification if they are semantically identical.
## Content
In the agent's thought process, it asked "Could it be just 'Roanoke'?" but rejected it. A better strategy is to accept the simpler form if it is supported by the text, as it often aligns better with ground truth annotations which tend to be concise.

ACTION: TASK_COMPLETE
