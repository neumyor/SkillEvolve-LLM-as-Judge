# Success Memory Item 1
## Title
Direct Context Extraction
## Description
Locate explicit statements in the retrieved context that directly map the query subject to the requested attribute.
## Content
Scan retrieved snippets for declarative sentences containing both the queried entity and the target information. Prioritize direct textual matches over inferred connections, especially when the context explicitly states the relationship without requiring intermediate steps.

# Success Memory Item 2
## Title
Strict Format Adherence
## Description
Enclose only the final extracted answer within the specified output tags, omitting all reasoning or supplementary text.
## Content
After identifying the correct answer, immediately format it using the required syntax (e.g., `<answer>Answer</answer>`). Ensure no additional commentary, steps, or explanations are included outside the tags to maintain strict compliance with evaluation requirements.

# Success Memory Item 3
## Title
Multi-Source Consensus Utilization
## Description
Leverage consistent information across multiple retrieved documents to solidify the extracted answer.
## Content
When several independent snippets explicitly state the same fact, prioritize this repeated information as the definitive answer. This approach streamlines decision-making for straightforward factual queries by relying on document agreement rather than complex reasoning or alternative hypothesis generation.
