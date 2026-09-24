# Success Memory Item 1
## Title
Cross-Attribute Intersection
## Description
Locate the target entity by identifying where multiple explicit constraints from the prompt converge within the retrieved context.
## Content
When a question combines distinct descriptors (e.g., geographic feature and administrative status), scan passages for direct statements that tie both conditions to a single named entity. Prioritize sentences that explicitly link all specified attributes simultaneously rather than assembling the answer from fragmented or separately mentioned facts.

# Success Memory Item 2
## Title
Primary Reference Prioritization
## Description
Resolve candidate ambiguity by defaulting to the most current or prominently cited entity when the prompt lacks temporal qualifiers.
## Content
If retrieved context presents multiple valid options (e.g., historical vs. present-day locations), select the one framed as the definitive or active answer in authoritative summaries. Reserve secondary or legacy candidates only when the question explicitly signals a historical, comparative, or time-bound focus.

# Success Memory Item 3
## Title
Direct Textual Alignment
## Description
Validate the selected answer by confirming it appears in unambiguous, declarative context passages before finalizing the output.
## Content
Before formatting the response, verify that at least one retrieved snippet explicitly states the connection between the question's criteria and the chosen entity. Rely on clear, standalone assertions rather than inferred relationships, ensuring the final answer directly mirrors the semantic structure of the original query.
