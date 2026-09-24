# Success Memory Item 1
## Title
Constraint Decomposition & Attribute Mapping
## Description
Systematically break down multi-part prompts into discrete qualifiers (e.g., temporal markers, platform, specific records) to create a precise filtering lens for evaluating retrieved context.
## Content
Parse the question into independent attributes such as year, media type, and notable achievements. Use these attributes to cross-reference against document snippets, ensuring each constraint aligns with the candidate answer before selection. This prevents misattribution when multiple entities share partial similarities.

# Success Memory Item 2
## Title
Corroborative Snippet Aggregation
## Description
Leverage consensus across multiple retrieved documents to validate the target entity, prioritizing direct textual matches over inferential leaps.
## Content
When several independent passages explicitly state the same fact or entity name, treat this convergence as strong evidence. Extract the exact phrasing used in the context to maintain fidelity to the source material and minimize fabrication, especially when dealing with niche trivia or historical records.

# Success Memory Item 3
## Title
Strict Format Compliance & Direct Extraction
## Description
Immediately isolate the core entity requested and wrap it in the designated output tags, omitting supplementary explanation in the final response block.
## Content
After identifying the correct answer through context matching, bypass conversational filler. Directly place the precise entity string inside the required delimiters to satisfy structural requirements while preserving factual accuracy. This ensures downstream parsers or evaluators receive clean, machine-readable outputs.
