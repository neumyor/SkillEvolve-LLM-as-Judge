# Success Memory Item 1
## Title
Consensus Definition Extraction for Clue-Based Queries
## Description
Map descriptive or clue-style prompts to their corresponding terms by identifying repeated, explicit definitional matches across retrieved sources.
## Content
When processing queries formatted as crossword clues, riddles, or direct definitions, scan the context for dictionary-style entries that explicitly link the description to a specific word. Prioritize snippets that use direct equivalence phrasing (e.g., "The [term] is...", "[Term]: to make the sound of..."). Once multiple independent sources converge on the same lexical match, extract that exact term and output it directly within the designated answer tags, suppressing synonyms, etymologies, or conversational filler.
