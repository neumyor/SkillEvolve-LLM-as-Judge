# Success Memory Item 1
## Title
Exact Phrase Matching for Clue-Style Queries
## Description
Leverage retrieved context containing verbatim or near-verbatim matches to trivia or riddle-like prompts.
## Content
When the question uses a declarative clue format, scan the context for identical phrasing. Treat these as high-confidence anchors, then cross-reference with surrounding documents to confirm the entity before formatting the final answer.

# Success Memory Item 2
## Title
Contextual Alignment Across Snippets
## Description
Confirm candidate answers by checking consistency across multiple retrieved documents.
## Content
When an initial match appears in one snippet, scan additional context pieces for matching attributes. Consistent details across sources increase confidence and reduce ambiguity before finalizing the response.

# Success Memory Item 3
## Title
Strict Output Formatting Compliance
## Description
Adhere precisely to requested output tags without adding conversational filler.
## Content
Always wrap the final answer in the specified XML-style tags. Omit reasoning, explanations, or extra text in the final output to meet evaluation metrics and system requirements.
