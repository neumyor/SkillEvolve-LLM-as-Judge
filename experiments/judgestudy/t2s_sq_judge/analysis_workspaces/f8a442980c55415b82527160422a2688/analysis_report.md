# Failure Cause Item 1
## Title
Incorrect Answer Span Selection (Full Name vs. Surname)
## Description
The agent correctly identified the entity (Chester A. Arthur) but selected the full name "Chester A. Arthur" as the answer span. The gold answer is "Arthur". The evaluation metrics show an EM of 0.0 but a sub-EM of 1.0, indicating that the agent's answer contains the gold answer as a substring. The failure is due to the agent not narrowing the span to the specific expected format (surname only) despite the context supporting references to the president as "Arthur".
## Content
The agent's reasoning confirmed the entity was Chester A. Arthur based on the clue "only U.S. President named Chester". However, it committed to the full name "Chester A. Arthur" in the final output. The gold answer is "Arthur". Since the context frequently refers to him as "Arthur" (e.g., "Arthur was named to...", "Arthur succeeded..."), the shorter span "Arthur" is fully supported by the retrieved context and matches the gold answer exactly. The agent should have recognized that providing the surname alone is sufficient and often preferred in such trivia formats when the first name is already prominent in the query or context.

# Failure Memory Item 1
## Title
Leveraging Sub-EM Score for Span Correction
## Description
When the sub-EM score is 1.0 but EM is 0.0, the candidate answer contains the gold answer as a substring. This indicates a span-boundary or normalization error rather than a factual error. The agent should consider extracting the minimal span corresponding to the gold answer if the context supports it.
## Content
In this case, the agent's answer "Chester A. Arthur" contained the gold answer "Arthur". Instead of keeping the verbose full name, the agent could have output "Arthur", which is a valid, concise answer supported by the text (which refers to him as "Arthur" in multiple passages). This strategy minimizes formatting mismatches against gold answers that may use standardized short forms.

# Failure Memory Item 2
## Title
Contextual Reference Validation for Short Spans
## Description
Before outputting a shortened answer span (like a surname), verify that the retrieved context explicitly uses that short form to refer to the entity. This ensures the correction is grounded in the available evidence and acceptable to a judge who relies solely on the context.
## Content
The agent initially outputted the full name. To correct this, we verified that the context documents (e.g., HISTORY.com, Wikipedia snippets) refer to the president as "Arthur" in isolation (e.g., "Arthur was sworn in...", "Arthur succeeded..."). This validation confirms that "Arthur" is a context-supported answer, making it a safe correction for the span-boundary issue.

ACTION: TASK_COMPLETE
