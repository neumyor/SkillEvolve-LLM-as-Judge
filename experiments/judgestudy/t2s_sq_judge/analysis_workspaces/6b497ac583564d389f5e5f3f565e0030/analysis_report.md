# Failure Cause Item 1
## Title
Orthography Mismatch in Entity Selection
## Description
The agent correctly identified the musical but selected the two-word spelling "Show Boat" found in the context, whereas the gold answer requires the single-word spelling "Showboat".
## Content
The retrieved context documents consistently use the two-word title "Show Boat" (e.g., "Show Boat: Cotton Blossom...", "Musical Numbers for Show Boat"). The agent faithfully extracted this surface form. However, the benchmark's gold answer is "Showboat". This is a canonicalization error: the agent did not normalize the entity name to the single-word form expected by the evaluation metric, resulting in a 0.0 EM/F1 score despite identifying the correct entity.

# Failure Memory Item 1
## Title
Canonicalize Entity Spelling Beyond Context Surface Forms
## Description
When the context provides a valid but non-canonical spelling of an entity (e.g., multi-word vs. single-word), agents should prefer the canonical form if inferable, as benchmarks often enforce specific orthography.
## Content
Retrieved snippets may use varied formatting for the same entity (e.g., "Show Boat" vs "Showboat"). Agents should recognize that these refer to the same entity and, when the task implies a specific canonical answer, output the standardized form rather than strictly copying the context's formatting. This prevents false negatives due to minor orthographic differences.

# Failure Memory Item 2
## Title
Diagnose Near-Miss Failures as Orthography/Spacing Issues
## Description
When F1/EM is 0.0 but the agent's answer clearly points to the correct entity, check for spacing, capitalization, or punctuation differences against the gold answer.
## Content
A near-miss where the agent identifies the correct entity but fails on exact string match is often a formatting issue. Analysts should identify if the difference is purely orthographic (e.g., "Show Boat" vs "Showboat") and correct the output to match the expected canonical form without changing the underlying semantic choice.

ACTION: TASK_COMPLETE
