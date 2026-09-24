# Success Memory Item 1
## Title
Strip Non-Semantic Metadata Suffixes
## Description
Ignore trailing numbers, point values, or clue indices in prompts that do not change the core query intent.
## Content
Dataset or trivia-style questions often append metadata like `(15)`, `[1]`, or score indicators. Treat these as formatting noise rather than semantic components. Extract only the subject-action phrase to drive retrieval and reasoning, preventing unnecessary complexity or misinterpretation.

# Success Memory Item 2
## Map Narrative Descriptors to Canonical Names
## Description
Synthesize varied contextual aliases (e.g., "imp," "tiny man," "elf") to resolve the single proper noun the prompt expects.
## Content
Retrieved passages frequently describe the same entity using different narrative labels or roles. Cross-reference these descriptors to converge on the most widely recognized proper noun. Prioritize the canonical identifier over literal descriptive phrases when the prompt structure implies a specific named answer.

# Success Memory Item 3
## Leverage Cross-Doc Consensus for Validation
## Description
Use agreement across multiple independent snippets to confirm the answer, reducing reliance on any single potentially ambiguous passage.
## Content
When several context blocks independently highlight the same core fact or entity, treat this convergence as strong signal validation. This approach filters out outlier details and ensures the final response aligns with the dominant evidence pattern present in the retrieved set.
