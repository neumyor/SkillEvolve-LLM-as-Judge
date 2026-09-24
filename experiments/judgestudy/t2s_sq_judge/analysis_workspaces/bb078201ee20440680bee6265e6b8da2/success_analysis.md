# Success Memory Item 1
## Title
Direct Span Extraction via Verbatim Overlap
## Description
When prompts resemble standardized trivia or quiz formats, rapidly scan retrieved snippets for exact or near-exact phrasing matches to locate the answer span without extensive inference.
## Content
Align core question keywords with context text to identify precise answer locations. Prioritize documents where the query structure directly maps to a single line or segment, enabling immediate extraction rather than multi-step reasoning.

# Success Memory Item 2
## Title
Structural Delimiter Utilization
## Description
Exploit common formatting markers (e.g., pipes, colons, or brackets) embedded in curated QA contexts to cleanly separate the prompt portion from the target answer.
## Content
Identify separator characters that divide the statement/question from the expected response. Use these boundaries to isolate the exact answer string, reducing parsing errors and ensuring precise extraction from dense or mixed-format snippets.

# Success Memory Item 3
## Title
Constraint-Driven Output Formatting
## Description
Enforce strict output templates immediately upon answer identification to maintain compliance and prevent reasoning leakage.
## Content
Wrap the extracted span in the required tags before finalizing the response. Skip explanatory text or intermediate validation steps outside the designated format to guarantee adherence to system instructions and preserve token efficiency.
