# Success Memory Item 1
## Title
Isolate Explicit Temporal-Role Constraints
## Description
Extract precise role and date parameters from the prompt to serve as the primary search anchor, disregarding potentially noisy or stylized surrounding text.
## Content
When prompts contain bracketed or parenthetical identifiers (e.g., titles paired with year ranges), treat them as definitive filters. Search the retrieved context specifically for entities matching these exact parameters rather than relying on broader semantic similarity.

# Success Memory Item 2
## Title
Prioritize Direct Factual Matches
## Description
Match constrained queries directly to explicit contextual statements that mirror the prompt's role and timeframe structure.
## Content
Favor passages that explicitly state an entity held a specific position during the queried period. Use these direct factual alignments as the primary evidence base, ensuring the extracted answer corresponds exactly to the matched entity.

# Success Memory Item 3
## Title
Disambiguate Using Explicit Labels Over Implicit Relations
## Description
When multiple related roles share overlapping timeframes, rely on the prompt's explicit title designation to select the correct entity.
## Content
If contextual clues suggest alternative positions (e.g., vice presidency vs. presidency for the same years), default to the entity explicitly named in the prompt's title constraint. Trust direct labeling over inferred hierarchical or relational connections.
