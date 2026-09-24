# Success Memory Item 1
## Title
Direct Lexical Matching for Factoid Retrieval
## Description
Prioritize extracting answers by scanning context for exact or near-exact keyword overlaps between the query and document snippets, especially in definitional or Q&A formats.
## Content
When processing trivia or definition-based questions, immediately filter retrieved documents for phrases that mirror the question's core terms. Extract the answer directly from passages structured as explicit Q&A pairs, glossaries, or flashcards, as these often contain verbatim answers without requiring complex inference.

# Success Memory Item 2
## Title
Multi-Snippet Consistency Check
## Description
Validate candidate answers by confirming their consistent application across multiple independent context snippets.
## Content
After isolating a potential answer from a direct lexical match, scan additional relevant passages to ensure the term is uniformly used to describe the target concept. This cross-referencing step confirms contextual alignment and prevents misinterpretation of ambiguous or polysemous terms.

# Success Memory Item 3
## Title
Constraint-First Output Formatting
## Description
Structure the final response to strictly satisfy explicit formatting instructions before generating explanatory text, ensuring compliance and machine-readability.
## Content
Always place the required answer tags at the end of the response or isolate them clearly according to the prompt's specifications. Avoid embedding the constrained output within conversational prose, and ensure the exact string inside the tags matches the distilled answer without extra punctuation or qualifiers.
