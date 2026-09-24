# Success Memory Item 1
## Title
Decompose Query into Subject and Target Attribute
## Description
Isolate the central entity mentioned in the prompt and clearly define the specific missing information being requested.
## Content
Treat the question as a structured lookup task. Explicitly separate the known variable (e.g., historical figure) from the unknown variable (e.g., associated location or title) to guide focused document scanning rather than passive reading.

# Success Memory Item 2
## Title
Prioritize Explicit Contextual Matches
## Description
Search retrieved passages for direct textual links connecting the subject to the target attribute, favoring unambiguous statements over contextual inference.
## Content
When scanning documents, identify sentences that explicitly name both the subject and the requested detail. Rely on repeated, direct phrasing across multiple sources to establish high confidence in the extracted value before proceeding.

# Success Memory Item 3
## Title
Execute Direct Extraction and Strict Formatting
## Description
Convert the confirmed finding into the exact requested format, omitting supplementary details or alternative interpretations.
## Content
Once the target value is isolated, output only the precise term or phrase that satisfies the query. Wrap the result in the required structural markers immediately to ensure strict compliance with output specifications.
