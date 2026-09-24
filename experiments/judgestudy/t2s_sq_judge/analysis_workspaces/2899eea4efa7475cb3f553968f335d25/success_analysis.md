# Success Memory Item 1
## Title
Multi-Entity Attribute Isolation
## Description
Decompose compound queries referencing multiple subjects into individual lookup tasks, extracting the target attribute for each subject separately before comparing results.
## Content
Parse the prompt to identify every distinct event, person, or object mentioned. Scan the retrieved context for explicit statements linking each subject to the requested trait. Record the isolated attribute for each entity independently, then align the extracted values to determine the shared characteristic or category.

# Success Memory Item 2
## Title
Multi-Snippet Attribute Confirmation
## Description
Leverage overlapping information across multiple retrieved documents to confirm attribute accuracy, reducing reliance on single-point evidence.
## Content
When the context contains multiple snippets mentioning the same entities, compare their descriptions of the target trait. Prioritize consistent findings across independent sources. Use agreement between snippets to solidify the extracted attribute, ensuring the final synthesis rests on corroborated context rather than isolated mentions.

# Success Memory Item 3
## Title
Categorical Abstraction for Shared Traits
## Description
Translate specific instance details into the broader categorical term requested by the prompt when the question asks for a common species, type, or class.
## Content
Recognize when the prompt seeks a unifying category rather than individual names. Map specific identifiers (e.g., proper nouns or descriptive phrases) to their underlying classification. Output only the generalized category that satisfies the shared-trait condition, ensuring the phrasing directly completes the prompt's sentence structure.
