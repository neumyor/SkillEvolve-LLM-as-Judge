# Success Memory Item 1
## Title
Leverage Exact-Phrase Matching for Clue-Style Prompts
## Description
When questions adopt trivia or quiz formats, search results frequently reproduce the exact prompt text. Prioritize snippets containing the full query string to rapidly isolate the target answer without extensive parsing.
## Content
Recognize structured clue patterns in the input. Scan retrieved documents for verbatim matches of the prompt. Extract the missing entity directly from the surrounding sentence in the matching snippet, treating the snippet itself as the primary evidence source.

# Success Memory Item 2
## Title
Cross-Reference Actor-Character-Year Triads
## Description
For entertainment trivia, confirm the correct title by locating multiple context snippets that consistently pair the specified actors, character names, and release year.
## Content
Extract core entities (performer names, character identifiers, release year). Filter retrieved documents to find independent sources that link these elements to a single title. Select the title that maintains consistent alignment across all extracted entities.

# Success Memory Item 3
## Title
Enforce Clean Tagged Extraction
## Description
Maintain strict compliance with output constraints by isolating the final answer into a concise string and wrapping it exclusively in the required XML tags, excluding all reasoning or contextual filler.
## Content
After identifying the target entity, remove modifiers, alternative spellings, or explanatory phrases. Place only the canonical answer string between the opening and closing tags. Perform a final visual check to ensure tags enclose only the answer and nothing else.
