# Failure Cause Item 1
## Title
Span-boundary truncation: agent answered "Superior" instead of "Lake Superior"
## Description
The agent correctly identified the missing Great Lake as Superior through elimination (the question lists Huron, Ontario, Michigan, Erie, leaving Superior). It also correctly reasoned that "Superior" implies greatness. However, the agent committed to the answer span "Superior" rather than the fuller "Lake Superior" which appears explicitly in the context (e.g., Discover Canada passage: "Lake Superior. Lake. Michigan. Lake. Huron..."). The gold answer is "Lake Superior". The F1 score of 0.667 confirms partial overlap — "Superior" is a substring of "Lake Superior" but not the full expected span.
## Content
The agent's diagnostic reasoning was sound: it found the missing lake by comparing the question's list against the five known Great Lakes. But when extracting the final answer span, it chose only the distinctive word "Superior" instead of the complete entity reference "Lake Superior" used in the context. This is a classic span-boundary error — the agent knew the right entity but selected an incomplete text span. The context unambiguously supports "Lake Superior" as the answer, and the judge confirmed the correction.

# Failure Memory Item 1
## Title
Prefer the full entity span from context over the bare name
## Description
When the question lists entities without prefixes (e.g., "Huron" instead of "Lake Huron"), do not assume the answer should omit the prefix. Check whether the context uses a fuller form (e.g., "Lake Superior") and extract that complete span. The context's phrasing is the ground truth for span selection.
## Content
In this case, the question listed lakes as "Huron, Ontario, Michigan, Erie" without "Lake" prefixes, leading the agent to drop "Lake" from its answer. But multiple context passages explicitly use "Lake Superior". Always align your answer span with how the context refers to the entity, not with how the question abbreviates it.

# Failure Memory Item 2
## Title
Verify answer span completeness before committing
## Description
After identifying the correct entity, re-read the supporting context passage to confirm the exact span used. If the context says "Lake Superior" and you plan to answer "Superior", ask whether the context would support your chosen span. If the context consistently uses the fuller form, use it.
## Content
This prevents sub-EM errors where the answer is a substring of the correct span. A quick verification step — checking that your proposed answer span appears verbatim in the supporting passage — catches these boundary mistakes before output.

ACTION: TASK_COMPLETE
