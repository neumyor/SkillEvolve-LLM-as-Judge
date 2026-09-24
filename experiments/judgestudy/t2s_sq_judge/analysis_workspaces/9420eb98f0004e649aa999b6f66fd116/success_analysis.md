# Success Memory Item 1
## Title
Multi-Attribute Entity Resolution
## Description
Systematically cross-reference multiple distinct biographical clues from the prompt against retrieved documents to isolate a single matching candidate.
## Content
When a query lists several specific identifiers (e.g., former role, location, notable works, career trajectory), scan the context to find one entity that satisfies every condition simultaneously. Prioritize candidates where all clues converge rather than accepting partial matches.

# Success Memory Item 2
## Title
Contextual Orthography Normalization
## Description
Identify and correct minor typographical or OCR artifacts in proper nouns during answer extraction.
## Content
Retrieved text often contains character substitution or omission errors in names. Match the corrupted string to its intended real-world entity using surrounding contextual clues, then output the standardized, widely accepted spelling in the final answer.

# Success Memory Item 3
## Title
Constraint-Aligned Output Wrapping
## Description
Isolate the synthesized answer and enclose it strictly within the requested delimiters.
## Content
After confirming the answer through clue mapping and normalization, place only the final entity name inside the designated tags. Omit explanatory text, reasoning steps, or conversational filler to ensure direct compatibility with automated parsing and evaluation.
