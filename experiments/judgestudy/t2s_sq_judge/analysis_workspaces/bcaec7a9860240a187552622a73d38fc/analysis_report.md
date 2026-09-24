# Failure Cause Item 1
## Title
Over-generalization of Entity Name
## Description
The agent correctly identified the historical event (admission to the U.N. in 1971) but substituted the precise entity name "People's Republic of China" with the broader term "China".
## Content
The retrieved context explicitly names "People's Republic of China" in the passage title ("Oct. 25, 1971 | People's Republic of China In, Taiwan Out, at U.N.") and references "P.R.C." in the body text. The agent recognized this information but decided "China" was sufficient, failing to extract the exact span provided by the source. This loss of precision caused the EM/F1 mismatch despite achieving sub-EM success, as the benchmark expects the specific formal entity name present in the context.

# Failure Memory Item 1
## Title
Prefer Exact Entity Spans from Source Text
## Description
When the context provides a specific political or formal entity name, prefer extracting that exact span over a common shorthand or broader synonym.
## Content
Trivia and QA tasks often require the precise entity as stated in the source material. If a passage titles an article "People's Republic of China..." or uses "P.R.C.", the answer should match that specific phrasing rather than defaulting to "China" unless the question explicitly asks for the common name. This avoids unnecessary precision loss and ensures alignment with expected answer strings.

# Failure Memory Item 2
## Title
Align Answer Granularity with Source Terminology
## Description
Match the granularity of the answer to the terminology used in the supporting passage, especially when distinguishing between related entities.
## Content
In contexts involving political entities, dates, or formal admissions, the source text often contains the exact expected answer string. Agents should prioritize extracting the full, formal name when available in the context rather than abbreviating or generalizing, ensuring the output matches the specific entity referenced by the retriever.

ACTION: TASK_COMPLETE
