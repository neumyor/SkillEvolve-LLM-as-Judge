# Success Memory Item 1
## Title
Direct Semantic Mapping from Prompt to Context
## Description
Align the definitional phrase in the question with explicit meaning entries in the retrieved documents to isolate candidate answers.
## Content
Scan context for exact or near-exact matches to the target definition. Filter out tangential information and extract only entries that directly state the requested meaning, treating the prompt's phrasing as a strict semantic filter.

# Success Memory Item 2
## Title
Distinguish Complete Entities from Morphological Components
## Description
When the prompt requests a specific named entity, differentiate between full standalone names and partial prefixes, suffixes, or root words that only partially satisfy the definition.
## Content
Evaluate candidates against the prompt's categorical constraint (e.g., "name" vs. "prefix"). Prefer the complete, independently used form when both a component and its full compound are present, as components often serve as building blocks rather than standalone answers.

# Success Memory Item 3
## Title
Leverage Repetition and Explicit Popularity Cues
## Description
Use frequency of mention across multiple documents and explicit descriptors like "common" or "popular" to resolve ambiguity among valid candidates.
## Content
Compare all semantically matching candidates. Prioritize the one most frequently cited or explicitly labeled as common/popular in the context, ensuring alignment with the prompt's specificity requirements and real-world usage patterns.
