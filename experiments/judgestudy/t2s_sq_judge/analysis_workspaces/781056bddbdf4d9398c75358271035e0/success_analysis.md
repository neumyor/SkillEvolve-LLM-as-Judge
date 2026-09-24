# Success Memory Item 1
## Title
Multi-Constraint Entity Resolution
## Description
Systematically align each descriptive clause in the prompt with the retrieved context to identify converging evidence for a single target entity.
## Content
Decompose the question into distinct attributes (e.g., nationality, era, specific work, artistic period). Scan the context for passages that simultaneously satisfy all attributes, filtering out partial or tangential matches until only one candidate consistently fulfills every constraint.

# Success Memory Item 2
## Title
Keyword-Guided Passage Validation
## Description
Leverage unique proper nouns and temporal markers from the query to quickly locate and cross-reference supporting evidence across multiple context snippets.
## Content
Extract high-signal terms (e.g., artwork title, time period, demographic descriptors) and use them to filter retrieved documents. Prioritize passages that explicitly link these terms together, using overlapping mentions across different sources to reinforce confidence in the match before proceeding to extraction.

# Success Memory Item 3
## Title
Concise Identifier Extraction
## Description
Isolate the precise named entity from validated context passages while discarding ancillary details, then apply strict formatting rules for the final output.
## Content
Once the target entity is confirmed through context matching, extract only its canonical name. Avoid paraphrasing or appending explanatory clauses unless grammatically required, and ensure the result strictly adheres to the specified output container tags without additional commentary.
