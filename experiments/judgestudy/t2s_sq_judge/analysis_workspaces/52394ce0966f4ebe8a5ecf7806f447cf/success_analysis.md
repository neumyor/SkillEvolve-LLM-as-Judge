# Success Memory Item 1
## Title
Direct Value-to-Entity Alignment
## Description
When a query specifies a numerical threshold, score, or condition, prioritize locating explicit context statements that directly equate that value to a specific term.
## Content
Scan retrieved passages for exact phrasing patterns such as "[Term] scores/values [Number]" or "[Condition] yields [Number]". Extract the associated term as the primary candidate. Avoid inferring composite scoring scenarios unless the question explicitly asks for cumulative or conditional point breakdowns.

# Success Memory Item 2
## Cross-Source Consensus Validation
## Description
Confirm initial candidates by checking whether multiple independent context snippets consistently define the same relationship between the queried condition and the target term.
## Content
If several distinct documents or paragraphs independently state the same rule or definition, treat the convergence as high-confidence evidence. Use this agreement to lock in the answer without introducing external assumptions or overcomplicating the extraction.

# Success Memory Item 3
## Constraint-Compliant Output Generation
## Description
Ensure the final response strictly adheres to formatting requirements while preserving lexical precision and natural phrasing.
## Content
Wrap the extracted answer exactly within the specified tags. Keep the output concise, matching the grammatical form implied by the question (e.g., including necessary articles or singular/plural forms) to maximize exact-match alignment with standard evaluation metrics.
