# Success Memory Item 1
## Title
Constraint Decomposition & Entity Mapping
## Description
Break multi-clause factoid questions into discrete attributes and systematically scan retrieved documents for overlapping mentions.
## Content
Isolate each defining condition (e.g., specific year, known work, scientific claim) from the prompt. Search the context for passages that explicitly link these conditions to a single named entity, ensuring every constraint is satisfied before proceeding.

# Success Memory Item 2
## Title
Cross-Document Consensus Building
## Description
Validate candidate answers by checking for consistent co-occurrence of attributes across multiple independent context snippets.
## Content
Do not rely on a single passage to satisfy all question constraints. Instead, aggregate evidence from several retrieved documents; if multiple sources independently connect the same individual to the specified timeframe, publication, and discovery, the match is highly reliable.

# Success Memory Item 3
## Title
Precision Extraction & Tag Adherence
## Description
Strip away contextual explanations and output only the exact target entity wrapped in the required formatting tags.
## Content
Once the correct entity is identified, extract precisely the requested name or value. Avoid including supporting details, quotes, or conversational filler in the final output, strictly wrapping the result in the mandated `<answer>...</answer>` structure.
