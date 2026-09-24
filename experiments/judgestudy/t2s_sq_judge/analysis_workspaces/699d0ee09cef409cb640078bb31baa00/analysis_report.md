# Failure Cause Item 1
## Title
Incorrect Answer Granularity and Span Selection
## Description
The agent misinterpreted the intent of a named-entity-only question, selecting a verbose descriptive phrase instead of the concise target entity.
## Content
The question "Sultan Haji Hassanal Bolkiah" is a named entity query expecting a specific attribute (in this case, the country "Brunei"). The agent instead treated it as a "who is this?" question, extracting the full opening clause "29th and current Sultan and Yang Di-Pertuan of Brunei" from the Wikipedia passage. While the context supports that he is the Sultan of Brunei, the agent failed to isolate the core entity "Brunei" as the expected answer span. This reflects a failure in recognizing the appropriate granularity for SearchQA-style entity queries, where the answer should be the minimal identifying attribute rather than a full biographical descriptor.

# Failure Memory Item 1
## Title
Prefer Concise Entity Spans for Named Entity Queries
## Description
When the question consists solely of a person's name, the expected answer is typically their primary attribute (e.g., country, title, profession) in its shortest form, not a full descriptive sentence.
## Content
In SearchQA tasks, questions like "[Person Name]" usually expect a single entity or short phrase as the answer (e.g., the country they are associated with). Agents should avoid extracting long clauses or sentences even if they contain the correct information. Instead, identify the specific attribute being queried and extract only that span. For example, if the context says "X is the ruler of Y," the answer should be "Y," not "ruler of Y" or "the ruler of Y."

# Failure Memory Item 2
## Title
Align Answer Length with Task Constraints
## Description
The task explicitly requests concise answers ("typically a few words or a short phrase"). Agents must enforce this constraint during span selection.
## Content
Even when the reasoning identifies the correct information, the final answer must adhere to the output format constraints. If the prompt specifies a concise answer, agents should trim descriptive phrases to their essential core. Over-extraction leads to low F1/EM scores because the answer string becomes too dissimilar to the gold standard, even if semantically related. Always verify that the selected span matches the expected brevity before finalizing.

ACTION: TASK_COMPLETE
