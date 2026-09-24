# Success Memory Item 1
## Title
Explicit Attribute Mapping
## Description
Translate question descriptors into search anchors to locate direct matches in retrieved text.
## Content
Break down the prompt into core identifiers (e.g., spatial location, mechanical function). Scan context snippets for passages that explicitly pair these identifiers with a single named entity. Prioritize sentences that use direct definitional language rather than peripheral details.

# Success Memory Item 2
## Title
Cross-Passage Consensus
## Description
Confirm candidate answers by tracking repeated claims across multiple independent documents.
## Content
When several retrieved passages independently describe the same relationship or definition, treat this convergence as high-confidence evidence. Relying on overlapping statements minimizes noise from isolated or tangential snippets and stabilizes the selection process.

# Success Memory Item 3
## Title
Constraint-Aligned Formatting
## Description
Isolate the precise answer term and enclose it strictly within the requested structural markers.
## Content
Once the target entity is identified, discard surrounding explanatory text or full sentences. Output only the exact term inside the specified tags to satisfy parsing requirements and maximize scoring metrics.
