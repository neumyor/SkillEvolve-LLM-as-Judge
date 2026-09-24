# Success Memory Item 1
## Title
Multi-Constraint Parsing
## Description
Decompose identification questions into discrete, explicit entities to direct focused information retrieval and reduce ambiguity.
## Content
When a prompt contains multiple identifying details (e.g., performer, venue, year), extract each as a standalone constraint before processing retrieved text. This structured breakdown prevents conflation of similar subjects and creates a clear checklist for matching against documents.

# Success Memory Item 2
## Title
Concurrent Constraint Alignment
## Description
Confirm a candidate answer only when a single source simultaneously satisfies all extracted constraints, filtering out partial matches.
## Content
Cross-reference each parsed detail against the retrieved context. Prioritize documents where every key element appears together in close proximity. Disregard sources that satisfy only some conditions, as they typically point to related but incorrect entities or revivals.

# Success Memory Item 3
## Title
Strict Tag Adherence
## Description
Isolate the final answer within designated formatting markers, separating it from explanatory text to ensure parser compatibility.
## Content
After confirming the correct entity, place it exclusively inside the required tags (e.g., `<answer>...</answer>`). Keep surrounding reasoning separate and avoid embedding the answer in narrative sentences, as automated evaluators rely on exact tag boundaries for accurate scoring.
