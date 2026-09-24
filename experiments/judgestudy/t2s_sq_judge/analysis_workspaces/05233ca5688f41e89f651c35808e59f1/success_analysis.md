# Success Memory Item 1
## Title
Align Explicit Role Descriptors with Query Constraints
## Description
Map specific titles, statuses, or positions mentioned in the context directly to the subject description in the prompt to isolate the target entity.
## Content
When a question specifies a particular status (e.g., "former first lady," "president of [Country]"), scan retrieved snippets for exact or near-exact matches of those descriptors paired with candidate names. Prioritize entities where the role and political/geographic context explicitly overlap with the query, using the descriptor as the primary anchor rather than relying solely on dates or events.

# Success Memory Item 2
## Title
Filter Candidates Using Timeline and Jurisdiction Mismatches
## Description
Systematically rule out entities that appear in the context but fail to meet core temporal, geographic, or positional requirements.
## Content
Compare each named entity against the question's strict parameters (date, location, office). Discard matches that share superficial keywords but contradict established constraints (e.g., ruling out a sitting president when asked for a "former" official, or excluding figures from different countries despite shared campaign-related terminology). This prevents keyword-overlap traps and narrows the field to logically viable options.

# Success Memory Item 3
## Title
Infer Answers from Truncated Context Anchors
## Description
Extract the correct answer even when supporting text is cut off, by relying on strong entity-role pairs and corroborating timeframe markers.
## Content: If a snippet contains a highly relevant entity paired with the correct timeframe or event, treat it as a valid anchor. Cross-reference with adjacent phrases or standard list structures (e.g., "candidates, including...") to confirm the relationship. Trust explicit entity-role alignments in fragmented text over waiting for perfectly complete sentences, as partial matches often contain the decisive identifying information.
