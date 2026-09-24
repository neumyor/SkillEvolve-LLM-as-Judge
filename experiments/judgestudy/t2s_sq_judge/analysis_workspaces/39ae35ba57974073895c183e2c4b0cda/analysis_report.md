# Failure Cause Item 1
## Title
Span Boundary Over-Selection in Entity Identification
## Description
The agent correctly identified the target entity but included an unnecessary descriptor ("Desert") in the answer span, causing a mismatch with the expected minimal entity name.
## Content
The question asks to identify "this largest desert" based on a descriptive quote. The agent found the correct entity (Sahara) in the context but output "Sahara Desert" instead of just "Sahara". In many QA benchmarks, especially those derived from trivia or fill-in-the-blank formats, the gold answer is the core proper noun. Adding common nouns like "Desert" creates a near-miss that fails exact match metrics despite being semantically correct. The agent should prioritize extracting the shortest, most precise proper noun phrase that directly answers the question.

# Failure Memory Item 1
## Title
Prefer Minimal Proper Noun Spans
## Description
When the question identifies an entity by type (e.g., "this largest desert"), the answer should typically be just the proper name, not the type + name.
## Content
Avoid appending generic category words (Desert, City, River, Person) to the extracted entity name unless they are strictly part of the official proper name. If the context refers to the entity as "Sahara" and the question asks for the desert, output "Sahara". This reduces span-boundary errors and aligns with standard benchmark expectations for entity extraction.

# Failure Memory Item 2
## Title
Leverage Verbatim Quote Matching for Passage Selection
## Description
Use unique phrases from the question to locate the most relevant context passage.
## Content
The agent successfully used the distinctive phrase "Contrary to popular belief..." to find the matching snippet in the "sahara - Search-ID.com" document. This strategy of mapping unique question phrasing to specific context snippets is highly effective for disambiguation and should be consistently applied when multiple documents contain overlapping information.

# Failure Memory Item 3
## Title
Verify Answer Precision Against Question Constraints
## Description
Before finalizing, check if the extracted span contains redundant words relative to the question's framing.
## Content
If the question already specifies the entity type (e.g., "this largest desert"), the answer should ideally exclude that type word. Perform a quick sanity check: does the answer add information already implied by the question? If so, trim the span to the core entity.

ACTION: TASK_COMPLETE
