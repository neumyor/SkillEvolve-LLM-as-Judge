# Success Memory Item 1
## Title
Direct Epithet-to-Entity Mapping
## Description
Resolve possessive or location-based question phrases by locating exact entity matches in the context.
## Content
When a prompt uses a descriptive title or location suffix (e.g., "Rose of [Place]"), search the context for the corresponding full named entity. Anchor your extraction to this matched entity, then isolate only the specific component requested by the question's phrasing.

# Success Memory Item 2
## Title
Attribute Constraint Validation
## Description
Confirm extracted candidates satisfy all explicit contextual qualifiers before finalizing.
## Content
Cross-reference the isolated candidate against defining phrases in the retrieved text (e.g., administrative roles, geographic regions, or historical facts). Only proceed if the context explicitly confirms the candidate meets every constraint listed in the prompt.

# Success Memory Item 3
## Title
Strict Token Isolation & Tagging
## Description
Return only the exact requested term wrapped in the mandated structural tags.
## Content
Strip the final answer to its most concise form, removing titles, dates, or surrounding context. Enclose solely the target token within the required output tags to ensure exact string matching during evaluation.
