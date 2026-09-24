# Success Memory Item 1
## Title
Exact Phrase Matching for Descriptive Queries
## Description
Prioritize locating verbatim or near-verbatim matches of a question's unique descriptive clauses within retrieved context, as trivia and riddle-style prompts frequently reuse published phrasing.
## Content
Decompose the prompt into its core descriptive phrases. Scan context snippets for identical wording. When a match is found, extract the associated entity from the immediate surrounding text or document title, treating the context as a direct source rather than requiring complex inference.

# Success Memory Item 2
## Title
Attribute Mapping and Cross-Validation
## Description
Validate candidate answers by systematically mapping abstract question descriptors to concrete properties using domain knowledge or corroborating context hits.
## Content
Isolate key qualifiers (e.g., biological category, color, structural components). Test the extracted candidate against each qualifier. If multiple context passages reference the same candidate alongside related terms, use this convergence to confirm accuracy before finalizing the output.

# Success Memory Item 3
## Title
Source Format Adaptation
## Description
Adjust extraction strategy based on the apparent origin of the context, particularly recognizing quiz databases, trivia columns, or recipe aggregators as high-yield answer repositories.
## Content
Identify contextual markers such as "Trivia," "Q&A," "Recipe," or structured clue formats. For these sources, bypass lengthy reasoning chains and directly map the query to the corresponding answer field or title. Leverage the predictable structure of these formats to accelerate response generation.
