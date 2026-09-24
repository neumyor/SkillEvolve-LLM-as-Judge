# Failure Cause Item 1
## Title
Misleading Document Title Bias
## Description
The agent incorrectly prioritized a document title ("Air Force Plant 16") over the explicit textual evidence regarding the assembly location.
## Content
The agent saw a document titled "Air Force Plant 16 - California State Military Museum" and assumed this was the specific military facility where Discovery was assembled. However, the text within that document only states that "final assembly is at Palmdale," and other documents consistently refer to the location simply as "Palmdale" or "Palmdale, Calif." The agent committed to "Air Force Plant 16" due to title prominence rather than extracting the actual location span supported by the narrative text.

# Failure Memory Item 1
## Title
Prioritize Narrative Text Over Titles for Location Spans
## Description
When identifying a location entity, rely on the descriptive text in the passage rather than assuming the document title contains the precise answer span.
## Content
Document titles often contain metadata, museum names, or broader categories (e.g., "California State Military Museum") that do not directly answer the specific question. The agent should extract the exact location phrase used in the sentence describing the event (e.g., "assembly... at Palmdale") instead of guessing from the title.

# Failure Memory Item 2
## Title
Avoid External Knowledge Contradiction When Context is Ambiguous
## Description
Do not introduce external knowledge (like Air Force Plant 42 vs 16) when the provided context uses a simpler, repeated term.
## Content
The agent hesitated between "Air Force Plant 16" and "Air Force Plant 42" based on outside knowledge. In retrieval-augmented tasks, if the context consistently uses a generic term like "Palmdale" or "Palmdale assembly facility," the model should stick to that span rather than attempting to resolve real-world naming discrepancies that are not present in the source text.

ACTION: TASK_COMPLETE
