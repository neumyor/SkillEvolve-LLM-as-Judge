# Failure Cause Item 1
## Title
Over-Specification of Entity Name
## Description
The agent correctly identified the sport but output "American football" instead of the more generic term "Football". The retrieved context uses the terms "NFL football" and "football" repeatedly. While "American football" is factually correct, the question's phrasing and the context's terminology align better with the simpler answer "Football". The agent committed to a more specific variant ("American football") when the context and likely expected answer supported the broader term.
## Content
The agent's reasoning explicitly considered both "American football" and "Football", stating "I will answer 'American football' or 'Football'... I'll stick with American football." This decision to prefer the more specific label over the one directly matching the document titles (e.g., "What Is the Official Size of the NFL Football?") led to a sub-EM mismatch. The correction to "Football" aligns with the context's explicit use of "football" and the gold answer.

# Failure Memory Item 1
## Title
Prefer Context-Aligned Terminology for Answer Spans
## Description
When multiple valid answer spans exist (e.g., "American football" vs. "Football"), prioritize the term that most closely matches the terminology used in the retrieved context documents, especially if those documents are titled with that specific term.
## Content
In this case, the LIVESTRONG document is titled "What Is the Official Size of the NFL Football?" and refers to it as "football". The Infoplease document lists "football" among sports. Choosing "Football" over "American football" reduces the risk of span-boundary or synonym mismatches against the expected answer format, which often mirrors the source text's primary entity name.

# Failure Memory Item 2
## Title
Avoid Unnecessary Disambiguation When Context Supports Generic Term
## Description
If the context supports a generic entity name (e.g., "Football") and the question does not require disambiguation from other similar entities (e.g., soccer), avoid adding qualifiers (e.g., "American") unless explicitly necessary.
## Content
The agent added "American" to "football" despite the context not distinguishing it from other types of football in a way that requires such specificity for the answer. The judge accepted "Football" because the context explicitly links the dimensions to "NFL football", making "Football" a sufficient and accurate answer. Over-specifying can lead to exact match failures even when the semantic meaning is correct.

ACTION: TASK_COMPLETE
