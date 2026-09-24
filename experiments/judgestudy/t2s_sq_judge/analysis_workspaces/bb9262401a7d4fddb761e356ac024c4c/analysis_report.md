# Failure Cause Item 1
## Title
Span Over-Specification: Substituting External Knowledge for Context Text
## Description
The agent correctly identified the relevant passages but replaced the exact context span "George Bush" with the more precise "George H. W. Bush" based on external knowledge or other context sentences. This caused a mismatch because the gold answer and the supporting sentence specifically use "George Bush".
## Content
In reading comprehension tasks, the model must prioritize extracting the exact phrase used in the supporting context over refining it with outside knowledge. When the context says "As President of the Senate, George Bush...", the answer should be "George Bush", not "George H. W. Bush", unless the context itself uses the fuller name in that specific reference.

# Failure Memory Item 1
## Title
Prefer Exact Context Spans Over External Knowledge Refinements
## Description
When extracting answers from retrieved context, always use the exact wording found in the supporting passage, even if a more precise or disambiguated version exists in your training data or other parts of the context.
## Content
If the context states "George Bush" in the relevant sentence, output "George Bush". Do not add middle initials, suffixes, or full formal names unless they appear in the specific sentence answering the question. This prevents near-miss errors where the entity is correct but the string does not match the expected span.

# Failure Memory Item 2
## Title
Align Answer Granularity with the Question's Referential Frame
## Description
Match the level of detail in the answer to how the entity is described in the specific context sentence that aligns with the question's constraints (date, role, event).
## Content
The question specifies "president of the Senate" and "Jan. 4, 1989". The matching passage uses "George Bush". The answer should mirror this exact referent. Cross-referencing other passages that might use "George H. W. Bush" is unnecessary and potentially harmful if those passages do not contain the exact span required by the question's framing.

ACTION: TASK_COMPLETE
