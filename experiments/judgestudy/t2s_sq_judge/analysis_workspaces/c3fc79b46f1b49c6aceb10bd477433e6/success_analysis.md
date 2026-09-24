# Success Memory Item 1
## Title
Leverage Structural Delimiters in Raw Data Sources
## Description
Identify and utilize common separators (e.g., pipes, commas, colons) in scraped datasets or quiz files to map queries directly to their corresponding answers.
## Content
When retrieving raw dataset files (such as Jeopardy archives or trivia dumps), clues and answers are often separated by specific delimiters. Scan matched snippets for these markers; the target entity typically appears immediately after the delimiter following the query phrase.

# Success Memory Item 2
## Title
Prioritize Exact Phrase Matching for Trivia Queries
## Description
Treat trivia and fill-in-the-blank questions as direct string-matching tasks within retrieved contexts rather than requiring complex synthesis.
## Content
For straightforward factual or pop-culture questions, search the retrieved text for the exact wording of the prompt. When an exact match is found, extract the adjacent proper noun or title as the definitive answer without additional reasoning.

# Success Memory Item 3
## Title
Direct Extraction Over Contextual Synthesis
## Description
When a single retrieved snippet contains both the question premise and its resolution, use direct extraction instead of cross-referencing multiple documents.
## Content
Avoid aggregating information from several sources if one document already provides a complete, self-contained mapping between the prompt and the answer. Rely on the explicit pairing in the source text to ensure accuracy and reduce processing overhead.
