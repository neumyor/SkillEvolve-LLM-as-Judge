# Success Memory Item 1
## Title
Descriptive Prompt to Explicit Definition Mapping
## Description
Convert feature-based or riddle-style queries into targeted scans for exact definitional statements within the retrieved text.
## Content
When a question outlines physical properties or functions (e.g., "soft central part... contains nerves"), locate sentences that pair those descriptors with a specific noun. Extract the named term directly from the definition rather than synthesizing or inferring it.

# Success Memory Item 2
## Title
Cross-Source Terminology Alignment
## Description
Confirm the candidate term by ensuring multiple independent context passages consistently link the described features to the same label.
## Content
Scan separate document excerpts for parallel definitions. If different sources independently map the prompt's descriptors to the identical term, treat it as the definitive answer. This pattern confirms the term is widely recognized and accurately reflects the context.

# Success Memory Item 3
## Title
Strict Term Extraction and Formatting
## Description
Output only the precise technical term requested, wrapped in the required tags, without adding explanatory text.
## Content
For factual identification questions, prioritize brevity and exact match. Strip away surrounding context words, synonyms, or qualifiers unless they are part of the official name. Apply the mandated output wrapper immediately after confirming the term matches all contextual criteria.
