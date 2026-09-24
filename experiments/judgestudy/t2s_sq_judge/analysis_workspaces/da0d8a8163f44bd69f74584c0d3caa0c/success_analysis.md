# Success Memory Item 1
## Title
Targeted Entity-Role Parsing
## Description
Deconstruct the prompt to isolate the central figure and their specified role or attribute, then scan the context for explicit statements linking that figure to the missing entity.
## Content
When a question uses a descriptive clause (e.g., "[Person], this [Role]'s..."), treat it as a direct lookup instruction. Search retrieved documents for sentences that pair the named individual with the exact title/position mentioned, prioritizing direct assertions over implied connections.

# Success Memory Item 2
## Title
Redundant Context Cross-Reference
## Description
Leverage multiple independent context snippets that state the same fact to confirm accuracy before committing to a final answer.
## Content
If several retrieved passages contain overlapping information about the target relationship, mentally align them to verify consistency. This pattern-matching approach minimizes extraction errors and builds confidence without requiring external knowledge or complex inference.

# Success Memory Item 3
## Title
Strict Tag-Bound Output
## Description
Isolate the final extracted answer and place it exclusively within the required formatting tags, stripping all conversational text or reasoning steps.
## Content
After identifying the precise answer, format it exactly as instructed (e.g., `<answer>Exact Entity</answer>`). Ensure the final response contains zero preamble, explanation, or markdown outside the tags to guarantee clean parsing and compliance.
