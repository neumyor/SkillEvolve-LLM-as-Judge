# Success Memory Item 1
## Title
Exact String Matching for Clue-Based Queries
## Description
Identify when a question functions as a direct definition or flashcard prompt and locate the verbatim phrase within the retrieved context.
## Content
When a query mirrors a trivia clue or dictionary entry, search the context for an exact character match of the question text. The correct answer is almost always embedded in the same sentence or paragraph, appearing immediately after the matched clue or completing the definitional structure.

# Success Memory Item 2
## Title
Positional Extraction from Definitional Context
## Description
Isolate the target term by analyzing its syntactic relationship to the matched clue phrase.
## Content
Once the exact clue is found, parse the surrounding text to extract only the specific term being defined. Discard auxiliary explanations, examples, or unrelated glossary entries in the same document, focusing solely on the word or phrase that directly fulfills the prompt's definition.

# Success Memory Item 3
## Title
Syntax-Compliant Output Wrapping
## Description
Apply strict formatting rules during the final generation step to ensure structural correctness.
## Content
Strip the extracted term of surrounding punctuation, capitalization inconsistencies, or filler words. Enclose the clean result precisely within the required tags, ensuring the final string contains only the direct answer and adheres to the mandated output schema.
