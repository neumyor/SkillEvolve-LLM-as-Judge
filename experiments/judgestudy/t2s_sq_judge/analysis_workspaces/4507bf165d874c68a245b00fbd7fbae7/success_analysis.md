# Success Memory Item 1
## Title
Decode Quoted or Punned Terms
## Description
Treat words enclosed in quotation marks within trivia prompts as indicators of wordplay, literal references, or specific named entities rather than their standard dictionary definitions.
## Content
When a prompt places a common noun in quotes (e.g., "steak"), scan the retrieved context for proper nouns, dish names, or branded terms that match the spelling exactly. Map this literal match to the broader subject matter to resolve the intended reference before proceeding to factual verification.

# Success Memory Item 2
## Title
Cross-Reference Fragmented Clues
## Description
Trivia questions often distribute identifying information across multiple independent categories (titles, historical timelines, and cultural associations). Synthesize these separate data points to isolate the target entity.
## Content
Identify each distinct clue type in the prompt (e.g., aristocratic rank structure, chronological milestone, and associated cultural artifact). Search the context for documents containing overlapping matches for these clues, then merge the fragments to confirm the single correct subject that satisfies all conditions simultaneously.

# Success Memory Item 3
## Title
Extract Core Identifier from Title Prompts
## Description
When a question frames the answer as completing a title or phrase (e.g., "The [Rank] of this..."), output only the specific surname, location, or descriptor that fills the syntactic gap, rather than the full formal name or biographical details.
## Content
Parse the grammatical structure of the prompt to determine what component of an entity's name is being requested. During final formatting, strip away titles, honorifics, and middle names to return just the essential identifier that directly completes the prompt's phrasing.
