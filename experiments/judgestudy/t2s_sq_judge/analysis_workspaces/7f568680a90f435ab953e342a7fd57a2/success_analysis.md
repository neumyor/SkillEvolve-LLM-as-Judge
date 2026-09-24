# Success Memory Item 1
## Title
Leverage Exact Phrase Matches for Trivia-Style Queries
## Description
Identify when a question follows a definitional or clue-based structure and prioritize locating verbatim matches within the retrieved context to quickly anchor the target entity.
## Content
Scan all documents for sentences containing the exact phrasing of the prompt. When a match is found, extract the subject from the immediate context or document metadata. This approach efficiently resolves queries originating from quiz databases or standardized trivia formats without requiring complex inference.

# Success Memory Item 2
## Title
Corroborate Candidate Entities Using Multi-Source Feature Mapping
## Description
Confirm a preliminary answer by mapping the question's specific descriptive elements to those documented in separate, authoritative contexts.
## Content
After identifying a potential match, systematically check other retrieved documents to see if they list the same components, attributes, or classifications. Consistent alignment across multiple independent sources confirms the correct entity and filters out false positives from isolated or ambiguous snippets.

# Success Memory Item 3
## Title
Resolve Parent-Category Relationships from Modifier Phrasing
## Description
Interpret regional, stylistic, or historical modifiers as indicators that the expected answer is the broader parent category rather than the specific variant.
## Content
Parse phrases like "[Modifier] version of this instrument" to determine scope. When the prompt describes a subset but asks for the underlying object, default to the general class name. This aligns with standard encyclopedic and trivia conventions where variants are used to define the core subject.
