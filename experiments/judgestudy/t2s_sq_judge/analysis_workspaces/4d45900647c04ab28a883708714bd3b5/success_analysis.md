# Success Memory Item 1
## Title
Recognize and Parse Clue-Based Prompts
## Description
Identify when a question uses a narrative, quiz, or Jeopardy-style format rather than a direct factual query, and treat it as an entity-mapping task.
## Content
Isolate proper nouns, character names, author references, and distinctive phrases within the prompt. Use these markers to scan retrieved documents for exact or near-exact matches, prioritizing snippets that contain the full clue or its core components over generic background information.

# Success Memory Item 2
## Title
Cross-Reference Recurring Entities Across Snippets
## Description
Validate the target answer by checking for consistent mentions of the core subject across multiple retrieved documents.
## Content
When multiple context blocks share overlapping keywords (e.g., author name, character names, publication details), use this convergence to confidently isolate the primary subject. Discard tangential details or alternative works mentioned in passing, focusing only on the entity that satisfies all prompt conditions simultaneously.

# Success Memory Item 3
## Title
Enforce Constraint-First Output Generation
## Description
Prioritize strict adherence to output formatting rules, especially tag-based delimiters, by separating answer determination from final presentation.
## Content
Once the target answer is identified, immediately apply the required structural template (e.g., `<answer>...</answer>`) and strip all intermediate reasoning, conversational filler, or explanatory text from the final output. This ensures compliance with system constraints while maintaining response efficiency.
