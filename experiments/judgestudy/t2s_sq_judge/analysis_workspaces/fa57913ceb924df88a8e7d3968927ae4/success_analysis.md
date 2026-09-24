# Success Memory Item 1
## Title
Prioritize Direct Phrase Mapping
## Description
When context passages closely mirror the question's syntax or explicitly pair the query's descriptors with a proper noun, extract the entity directly without overcomplicating the reasoning.
## Content
Scan retrieved documents for sentences that contain both the key constraints from the prompt (e.g., nationality, profession, project/location) and a candidate name. If a passage structurally aligns with the question or uses identical terminology, treat it as a direct factual anchor. Bypass multi-hop inference when the text already provides an explicit subject-predicate match.

# Success Memory Item 2
## Title
Exploit Cross-Document Redundancy
## Description
Use consistent mentions across varied source types to rapidly confirm the correct entity and eliminate ambiguity.
## Content
In retrieval-augmented tasks, multiple unrelated documents (e.g., biographies, flashcards, exhibition notes) frequently repeat the same core fact. Identify this repetition pattern early; when several snippets independently name the same individual under the given constraints, accept it as the definitive answer. This consensus signal reduces the need for extensive cross-referencing or doubt resolution.

# Success Memory Item 3
## Title
Apply Constraint-to-Entity Filtering
## Description
Systematically isolate the prompt's defining attributes and filter the context to find the single entity satisfying all conditions simultaneously.
## Content
Break the question into discrete filters (e.g., "British", "sculptor", "UNESCO Paris"). Search the context holistically for a proper noun that satisfies every filter. Once found, verify that no other entity in the context competes for the same description. Output the matched entity immediately, maintaining strict adherence to the requested format.
