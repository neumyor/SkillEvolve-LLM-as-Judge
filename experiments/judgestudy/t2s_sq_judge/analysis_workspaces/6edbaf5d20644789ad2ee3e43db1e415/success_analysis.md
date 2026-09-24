# Success Memory Item 1
## Title
Direct Identifier Mapping
## Description
Match distinctive question cues (nicknames, titles, affiliations) directly against context phrases to rapidly isolate the target entity.
## Content
When a query specifies a unique moniker or professional role, scan the retrieved passages for exact lexical overlaps. Extract the associated proper noun immediately upon finding a direct phrase match, bypassing unnecessary inference or background synthesis.

# Success Memory Item 2
## Title
Contextual Convergence Confirmation
## Description
Leverage repeated mentions across independent context snippets to confirm entity accuracy before final extraction.
## Content
If multiple retrieved documents independently link the same identifier to a single entity, treat this internal consistency as strong confirmation. Prioritize extracting the consistently named entity to minimize misattribution or noise interference.

# Success Memory Item 3
## Title
Constraint-First Formatting
## Description
Strip all reasoning and supplementary text, outputting only the exact target string within the required delimiters.
## Content
After isolating the correct entity, remove all surrounding context, explanations, or conversational filler. Wrap solely the precise answer string in the mandated tags to strictly satisfy output constraints and prevent parsing failures.
