# Success Memory Item 1
## Title
Direct Institution-to-Jurisdiction Mapping
## Description
Identify the governing territory by locating the named legislative or judicial body in the context and extracting its associated geographic entity.
## Content
When a query specifies a parliament, court, or administrative institution, scan the retrieved text for the exact institution name. Extract the immediately associated location or jurisdiction mentioned alongside it, as reference materials typically define governmental bodies by their governing region.

# Success Memory Item 2
## Title
Multi-Attribute Constraint Alignment
## Description
Ensure the selected entity satisfies all distinct descriptors in the prompt before finalizing the answer.
## Content
Cross-reference every attribute in the question (e.g., specific institution, geographic region, political classification) against the context. Select the entity only when the text explicitly links all provided descriptors to a single target, avoiding assumptions or partial matches.

# Success Memory Item 3
## Title
Explicit Text Extraction & Tag Compliance
## Description
Prioritize direct textual matches over inference and strictly adhere to the requested output formatting.
## Content
Rely on unambiguous statements in the context (e.g., "X serves as the legislature for Y") rather than deriving relationships. Once confirmed, extract the exact entity name and wrap it in the specified tags without additional commentary or structural deviation.
