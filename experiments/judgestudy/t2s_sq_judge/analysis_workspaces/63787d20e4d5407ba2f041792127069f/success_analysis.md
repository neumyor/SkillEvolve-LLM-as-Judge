# Success Memory Item 1
## Title
Filter Candidates by Explicit Categorical Constraints
## Description
Use specific nouns in the prompt to eliminate semantically related but categorically mismatched entities from the context.
## Content
When the question requests a specific type of entity (e.g., "empire," "kingdom," "river"), actively compare all context matches against this category. Discard plausible but incorrect types (e.g., provinces, cities, or tribes) even if they share historical or geographical ties to the correct answer. Prioritize the entity that strictly satisfies the requested classification.

# Success Memory Item 2
## Title
Resolve Historical Aliases via Contextual Descriptors
## Description
Bridge gaps between archaic/historical names and modern references by leveraging explicit geographical or demographic descriptions in the retrieved text.
## Content
Identify the target subject by scanning context passages for phrases that map old names to current locations (e.g., "territory of the present-day western half of Hungary"). Use these explicit mappings to confirm the query's subject before selecting the final answer, avoiding assumptions that require external knowledge.

# Success Memory Item 3
## Title
Align Temporal Markers with Historical Periods
## Description
Cross-reference approximate dates or eras in the prompt with contextual expansion timelines to validate candidate answers.
## Content
If the question includes a timeframe (e.g., "around 14 A.D."), search context for corresponding historical phases, conquests, or administrative formations. Select the entity whose documented timeline aligns with the stated period, treating approximate dates as era indicators rather than requiring exact numerical matches. Ensure the chosen entity's incorporation or establishment phase fits the requested window.
