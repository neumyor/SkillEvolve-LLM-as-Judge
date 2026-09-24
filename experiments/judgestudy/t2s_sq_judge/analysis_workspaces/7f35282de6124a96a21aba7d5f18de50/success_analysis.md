# Success Memory Item 1
## Title
Resolve Implicit Subject Queries
## Description
Convert descriptive statements or partial formulas into direct identification tasks by inferring the missing subject.
## Content
When prompted with a defining property (e.g., "Its area equals..."), treat it as a request to name the corresponding entity rather than perform a calculation. Use the stated attribute to trigger a search for the matching concept, recognizing that the prompt implicitly asks "What has this property?"

# Success Memory Item 2
## Title
Map Attributes to Domain Concepts via Context
## Description
Align the given property with retrieved information to pinpoint the exact object or term.
## Content
Scan context snippets for direct correspondences between the stated formula/property and named entities. Prioritize consistent mentions across multiple sources to establish a reliable link between the attribute and its subject before proceeding to output.

# Success Memory Item 3
## Title
Isolate Core Noun Phrase for Output
## Description
Extract only the essential identifying term to satisfy strict formatting requirements.
## Content
After establishing the conceptual link, strip all surrounding explanation, derivation steps, or unit conversions. Return solely the precise noun phrase (e.g., "a circle") within the designated tags to ensure clean parsing and optimal exact-match scoring.
