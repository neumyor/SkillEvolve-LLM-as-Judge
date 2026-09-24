# Success Memory Item 1
## Title
Pattern-Matched Completion for Incomplete Queries
## Description
Treat trailing prepositions or open-ended phrases in questions as direct fill-in-the-blank prompts requiring exact lexical matching from the context.
## Content
When a question ends with an incomplete phrase (e.g., "became the Duchess of it"), immediately map the syntactic structure to the retrieved text. Search for the exact title or noun that completes the phrase rather than paraphrasing. Extract only the missing entity that directly satisfies the grammatical slot.

# Success Memory Item 2
## Title
Multi-Snippet Fact Alignment
## Description
Leverage repeated contextual statements to anchor the correct entity before extraction.
## Content
When multiple retrieved passages independently report the same factual detail, treat this repetition as the definitive source. Align the extracted answer strictly with the consistently stated phrase, bypassing peripheral biographical data or tangential mentions to ensure precision.

# Success Memory Item 3
## Title
Constraint-First Extraction Protocol
## Description
Isolate the precise target term during reasoning and enforce strict output formatting rules without embedding explanations in the final tag.
## Content
During step-by-step analysis, explicitly separate the reasoning phase from the output generation phase. Once the target entity is identified, place only that exact value inside the required response tags. Avoid adding qualifiers, full sentences, or conversational filler within the delimited answer block to ensure compliance and machine readability.
