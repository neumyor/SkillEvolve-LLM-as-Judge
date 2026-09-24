# Success Memory Item 1
## Title
Constraint-Driven Query Parsing
## Description
Systematically decompose trivia and factual queries into explicit constraints to guide retrieval and candidate selection.
## Content
When answering constrained questions, first isolate hard parameters such as exact word count, specific domain, named entities, or dates. Use these parameters as active filters during information gathering and as mandatory checkpoints during candidate evaluation to prevent overgeneralization or mismatched responses.

# Success Memory Item 2
## Title
Multi-Signal Context Consensus
## Description
Rely on converging references across multiple retrieved documents to confirm obscure, idiomatic, or historically nuanced answers.
## Content
For niche trivia or idiomatic expressions, prioritize answers that appear consistently across independent sources rather than relying on a single snippet. When multiple documents independently link the target concept to the prompt's specific clues (e.g., historical figures, dates, or definitions), treat this convergence as strong evidence for accuracy.

# Success Memory Item 3
## Title
Pre-Output Alignment Check
## Description
Conduct a final structural and semantic alignment pass against the original prompt requirements before formatting the response.
## Content
Before generating the final answer, explicitly re-evaluate the selected candidate against every constraint in the prompt (e.g., exact word count, domain specificity, historical reference alignment). Only proceed to output once all criteria are satisfied, ensuring strict adherence to the task instructions and minimizing formatting or logical errors.
