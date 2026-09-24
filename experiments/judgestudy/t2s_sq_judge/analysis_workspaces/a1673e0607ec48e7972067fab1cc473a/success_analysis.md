# Success Memory Item 1
## Title
Direct Keyword Mapping and Title Prioritization
## Description
Efficiently locate answers by scanning retrieved documents for exact matches of the question's core entities and descriptors, giving priority to document titles and explicit descriptive phrases.
## Content
When processing factual or trivia-style queries, immediately extract the key nouns and modifiers from the prompt. Search the context specifically for these terms in document titles and opening sentences, as they frequently contain the direct answer without requiring complex inference or external knowledge.

# Success Memory Item 2
## Title
Cross-Passage Confirmation
## Description
Validate the candidate answer by cross-referencing at least two independent context snippets that independently state the same fact or title.
## Content
Avoid relying on a single ambiguous passage. Instead, ensure the target entity is consistently referenced across multiple documents. This pattern matching reduces extraction errors and confirms that the selected term aligns with the broader provided context rather than isolated noise.

# Success Memory Item 3
## Title
Strict Output Segregation
## Description
Clearly separate analytical reasoning from the final response, ensuring only the distilled answer appears inside the required formatting tags.
## Content
Perform all step-by-step analysis, keyword matching, and synthesis outside the final answer block. Once the correct entity is isolated, strip away explanatory text and place only the precise answer within the specified tags to comply with strict parsing requirements and prevent format-related failures.
