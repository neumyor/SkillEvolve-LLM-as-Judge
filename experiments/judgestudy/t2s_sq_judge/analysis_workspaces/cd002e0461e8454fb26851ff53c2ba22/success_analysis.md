# Success Memory Item 1
## Title
Query Decomposition and Constraint Mapping
## Description
Break down multi-element questions into discrete factual constraints and explicitly map each to corresponding phrases in the retrieved context.
## Content
Isolate key identifiers from the prompt (e.g., publication year, work title, demographic descriptors) and search for their direct intersection in the context. This prevents overgeneralization and ensures the extracted answer satisfies every condition specified in the original query.

# Success Memory Item 2
## Title
Cross-Snippet Corroboration
## Description
Validate the identified target by checking for consistent evidence across multiple independent context snippets before finalizing the answer.
## Content
Rely on overlapping mentions across different documents rather than a single source. When multiple passages independently link the same set of constraints to a single entity, use that convergence as the primary signal for answer selection, minimizing reliance on potentially noisy or partial excerpts.

# Success Memory Item 3
## Title
Format-Compliant Extraction
## Description
Strip all contextual framing and metadata from the final output, delivering only the precise target string within the required structural tags.
## Content
After confirming the correct entity, remove surrounding explanations, dates, or biographical details. Output only the exact name or value requested, wrapped strictly in the mandated tags, to ensure machine readability and adherence to evaluation metrics.
