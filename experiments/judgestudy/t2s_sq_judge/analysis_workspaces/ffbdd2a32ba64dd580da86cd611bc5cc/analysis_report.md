# Failure Cause Item 1
## Title
Nickname vs. Formal Name Selection Error
## Description
The agent selected the common nickname "Patty Hearst" instead of the formal name "Patricia Hearst" when both variants were explicitly present in the retrieved context.
## Content
The agent's internal monologue acknowledged both "Patty Hearst" and "Patricia Hearst" but defaulted to the nickname. The retrieved context contained explicit mentions of "Patricia Hearst" (e.g., in the "New Focus on Old SLA Killing" snippet: "March 20, 1976 - Patricia Hearst is convicted..."). The agent failed to recognize that the gold standard typically requires the full legal name when available, leading to a mismatch despite identifying the correct entity.

# Failure Memory Item 1
## Title
Prioritize Formal Names Over Nicknames in Entity Answers
## Description
When an entity is referred to by both a nickname and a formal name in the context, agents should prefer the formal name for the final answer unless the question specifically implies otherwise.
## Content
Agents often default to the most frequent or prominent mention (usually a nickname like "Patty"). To align with ground truth expectations in factual QA benchmarks, agents should scan for the most formal or complete version (e.g., "Patricia Hearst") and use it as the primary answer span, ensuring better alignment with standard reference answers.

# Failure Memory Item 2
## Title
Contextual Name Variant Resolution Strategy
## Description
When multiple documents refer to the same person using different names, agents must adjudicate between variants by prioritizing formal identifiers.
## Content:
If the context provides both short/nickname forms and full/legal forms, the agent should extract the full form as the canonical answer. This generalizable rule prevents near-miss errors caused by selecting colloquial variants when the benchmark expects formal names.

ACTION: TASK_COMPLETE
