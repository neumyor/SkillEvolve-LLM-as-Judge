# Success Memory Item 1
## Title
Constraint-to-Entity Alignment
## Description
Map specific descriptive clues from the prompt directly to candidate entities in the retrieved context.
## Content
Extract unique identifiers from the question (e.g., originating program, broadcast network, medium/type) and scan the context for exact or semantically equivalent matches. Prioritize candidates that satisfy every constraint simultaneously rather than relying on partial keyword overlaps.

# Success Memory Item 2
## Title
Cross-Document Consensus Verification
## Description
Confirm entity selection by checking for consistent mentions across multiple independent context snippets.
## Content
When a potential answer appears, validate it against other retrieved documents. Repeated, uncontradicted references to the same entity across different sources provide high-confidence grounding and minimize reliance on isolated or potentially noisy passages.

# Success Memory Item 3
## Title
Structural Compliance Enforcement
## Description
Explicitly verify and apply required output delimiters before final generation.
## Content
Before producing the final response, isolate formatting instructions from the prompt. Wrap the core answer exactly as specified (e.g., within designated tags or brackets) to ensure downstream parsers or evaluation metrics can extract it without error.
