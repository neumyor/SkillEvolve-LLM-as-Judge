# Success Memory Item 1
## Title
Direct Textual Alignment for Clue-Based Prompts
## Description
When the query replicates a descriptive clue or list entry, prioritize exact string matching within the context to locate the paired answer rather than relying on external inference.
## Content
Trivia, flashcard, and ranked-list contexts routinely place the target entity immediately after the descriptive prompt. Scan for the exact phrasing of the question in the retrieved text and extract the name or identifier that directly terminates or follows that segment.

# Success Memory Item 2
## Title
Proximity-Based Entity Resolution
## Description
Use positional cues in structured documents to resolve identity questions, treating terms placed in parentheses or at the end of a line as the definitive answer to preceding descriptions.
## Content
Reference materials often format entries as `[Description]. (Answer)` or `[Description] Answer.`. When processing such structures, anchor the extraction window to the immediate vicinity of the matched description and select the closest proper noun or labeled term as the response.

# Success Memory Item 3
## Title
Schema-Compliant Output Generation
## Description
Once the target entity is isolated through context matching, immediately wrap it in the specified delimiter tags without appending explanations, alternatives, or confidence markers.
## Content
Strict adherence to output templates ensures successful parsing. After confirming the extracted term satisfies the prompt, bypass additional reasoning steps and directly emit the final payload using the exact requested tag structure.
