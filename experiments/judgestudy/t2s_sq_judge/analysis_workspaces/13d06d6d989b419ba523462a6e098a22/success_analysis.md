# Success Memory Item 1
## Title
Resolve Historical vs. Current Factual Claims
## Description
When a prompt contains a superlative or statistic that conflicts with present-day data, identify temporal markers in the context to align the query with its intended historical reference point.
## Content
Scan retrieved documents for phrases indicating past states (e.g., "once," "historically," "before [year]"). Treat the question as anchored to that timeframe rather than rejecting it due to modern updates. Prioritize the entity relationship over strict contemporary metric alignment.

# Success Memory Item 2
## Title
Detect Trivia and Puzzle-Style Phrasing
## Description
Recognize concise, declarative prompts that mirror crossword or quiz conventions, which typically rely on established cultural or historical associations rather than rigorous current accuracy.
## Content
Use stylistic cues (e.g., "this [descriptor] nation") to anticipate canonical answers. Validate the core subject-object link first, then accept supporting attributes if they match widely recognized or historically documented usage found in the context.

# Success Memory Item 3
## Title
Anchor on Direct Relationships Before Evaluating Secondary Metrics
## Description
Establish the fundamental entity connection (e.g., city-to-country) before processing conflicting or evolving quantitative descriptors like size, rank, or population.
## Content
Filter context for explicit relational statements first. Treat secondary attributes as confirmation signals rather than initial filtering criteria. This prevents premature rejection of valid answers when context contains overlapping, dated, or regionally varying metrics.
