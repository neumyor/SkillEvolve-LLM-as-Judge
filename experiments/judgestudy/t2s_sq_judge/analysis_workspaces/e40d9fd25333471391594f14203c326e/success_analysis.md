# Success Memory Item 1
## Title
Direct Lexical Alignment & Constraint Filtering
## Description
Match query descriptors to exact document phrasing, then apply explicit prompt constraints to eliminate semantically adjacent but imprecise alternatives.
## Content
When processing factual questions with retrieved context, prioritize exact lexical overlaps between the query's key modifiers and the source text. If multiple plausible entities emerge, systematically evaluate them against the prompt's explicit constraints (such as geographic origin, timeframe, or specific role) to discard tangentially related terms. Finalize only when the selected term directly fulfills all stated conditions, then apply the required output formatting.
