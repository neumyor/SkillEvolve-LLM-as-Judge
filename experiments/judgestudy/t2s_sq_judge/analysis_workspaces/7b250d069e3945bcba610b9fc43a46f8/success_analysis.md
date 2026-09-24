# Success Memory Item 1
## Title
Cross-Source Corroboration
## Description
Confirm factual answers by identifying consistent claims across multiple independent retrieved documents before extraction.
## Content
When addressing direct factual questions, scan all provided snippets for explicit statements containing the prompt's core entities. Prioritize information that appears repeatedly across different sources or document types. Extract the target term only after establishing that multiple independent passages independently support the same conclusion, reducing reliance on single-point references and increasing extraction reliability.

# Success Memory Item 2
## Title
Constraint-Aligned Output Isolation
## Description
Strip all reasoning and auxiliary text to deliver only the verified entity wrapped in the exact formatting tags specified by the prompt.
## Content
Once the correct answer is identified, immediately transition to output generation without including intermediate steps, alternatives, or explanatory notes. Apply the required structural wrapper (e.g., `<answer>...</answer>`) precisely around the extracted term. This ensures strict compliance with automated evaluation pipelines and prevents token waste or parsing failures caused by unrequested content.
