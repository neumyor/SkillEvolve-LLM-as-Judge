# Success Memory Item 1
## Title
Relational Keyword Mapping for Entity Identification
## Description
Locate the target entity by scanning context for exact matches to the question's relational or superlative descriptors.
## Content
When a query asks to identify an organization or concept based on a specific ranking or relationship (e.g., "largest museum of this institution"), search the retrieved documents for sentences containing those exact keywords. The sentence structure typically places the target entity adjacent to the relational phrase, allowing direct extraction without inference.

# Success Memory Item 2
## Title
Terminology Preservation During Extraction
## Description
Maintain the exact naming convention found in the source text to ensure semantic precision.
## Content
Extract the full proper noun or institutional title exactly as it appears in the matching context snippet. Avoid abbreviations or shortened forms unless explicitly stated in the source, as preserving the original terminology prevents ambiguity and aligns with strict string-matching evaluation criteria.

# Success Memory Item 3
## Title
Constraint-Compliant Output Formatting
## Description
Isolate the final extracted term and apply the required output wrapper without supplementary text.
## Content
Once the correct entity is identified, place it directly inside the mandated tags (e.g., `<answer>...</answer>`). Strip all reasoning steps, introductory phrases, and contextual explanations from the final output block to strictly adhere to parsing requirements and maximize automated scoring success.
