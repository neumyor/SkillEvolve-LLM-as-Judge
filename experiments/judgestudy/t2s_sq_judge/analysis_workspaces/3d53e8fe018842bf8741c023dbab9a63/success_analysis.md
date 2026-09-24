# Success Memory Item 1
## Title
Multi-Signal Keyword Convergence for Factual Extraction
## Description
Isolate the precise answer to constrained factual queries by identifying core semantic anchors in the prompt and confirming their co-occurrence across multiple retrieved documents before extracting the target entity.
## Content
Decompose the question into essential identifiers (e.g., temporal markers, geographic locations, named individuals, and associated events). Scan the provided context specifically for these identifiers appearing together. When multiple independent passages consistently point to the same entity as the direct answer, select that entity as the definitive response. Omit all contextual framing, explanations, or extraneous details, returning only the exact requested term wrapped in the designated output tags.
