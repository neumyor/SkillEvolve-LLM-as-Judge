# Success Memory Item 1
## Title
Constraint-Driven Entity Resolution with Noise Filtering
## Description
When answering factual or historical queries, systematically map prompt constraints against retrieved context, prioritizing consistent multi-source alignment while actively filtering out contradictory, tangential, or historically corrected references.
## Content
1. Extract explicit relational constraints from the question (e.g., specific individual, associated quote, familial or political tie).
2. Scan all context documents for direct matches linking these constraints together.
3. Identify and discard passages that introduce conflicting details, alternate subjects, or meta-commentary about historical accuracy, unless they directly override the primary constraint match.
4. Validate that the selected entity satisfies every condition in the prompt simultaneously before finalizing the response. Maintain strict adherence to the required output format.
