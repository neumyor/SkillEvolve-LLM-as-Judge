# Success Memory Item 1
## Title
Constraint-Driven Context Scanning
## Description
Decompose the prompt into core entities, temporal markers, and actions to filter retrieved text efficiently.
## Content
Extract key variables (who, when, what) from the question and scan context blocks for overlapping keywords. Prioritize passages that contain all constraints simultaneously to isolate the most relevant information quickly.

# Success Memory Item 2
## Title
Cross-Passage Corroboration & Distractor Elimination
## Description
Confirm candidate answers by comparing multiple context snippets and explicitly ruling out chronologically or factually mismatched alternatives.
## Content
When context contains related events or similar names, cross-reference dates and actors to ensure alignment. Actively discard options that match partial criteria but fail on specific constraints (e.g., wrong year or different commander) to prevent trap answers.

# Success Memory Item 3
## Title
Strict Tag-Based Output Formatting
## Description
Isolate the confirmed answer and enclose it exclusively within the required delimiters, omitting all intermediate reasoning.
## Content
Once the correct entity is confirmed, extract only the final term or phrase. Wrap it precisely in the specified tags (e.g., `<answer>...</answer>`) without adding explanatory text, ensuring direct compatibility with automated parsing requirements.
