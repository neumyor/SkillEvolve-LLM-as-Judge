# Success Memory Item 1
## Title
Multi-Clue Entity Binding
## Description
Treat distinctive descriptive features (e.g., a visual symbol paired with a translated phrase or motto) as simultaneous constraints to narrow down candidate entities.
## Content
When a query combines a non-textual descriptor with a specific quoted string, search the context for passages that explicitly link both elements to a single proper noun. Prioritize entities where the symbol and phrase co-occur in the same descriptive sentence, filtering out unrelated mentions of either element alone.

# Success Memory Item 2
## Title
Cross-Snippet Consensus Filtering
## Description
Validate entity identification by confirming that multiple independent context passages consistently associate the same attribute set with one name.
## Content
Scan retrieved documents for overlapping references to the target clues. If several sources independently map the specific symbol and motto to the same location or organization, adopt that name as the definitive answer. This approach neutralizes noisy or tangential information present in individual snippets.

# Success Memory Item 3
## Title
Direct Attribute Extraction
## Description
Bypass contextual narrative by isolating and extracting the exact proper noun immediately tied to the query's defining characteristics.
## Content
Locate sentences containing direct attribution phrasing (e.g., "The flag of [City] depicts...", "motto reads... which translates to..."). Extract the named entity positioned adjacent to these matching attributes. Do not infer or synthesize; rely solely on explicit textual pairing between the clue and the target name.
