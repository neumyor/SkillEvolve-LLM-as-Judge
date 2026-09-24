# Success Memory Item 1
## Title
Multi-Source Entity Consistency
## Description
Identify the target entity type requested and confirm its presence across multiple independent context snippets to establish high confidence.
## Content
When extracting factual answers, scan all provided documents for the specific entity type (e.g., city, person, date). Prioritize values that appear repeatedly across different sources within the context, as this pattern strongly indicates correctness and reduces reliance on single-point data.

# Success Memory Item 2
## Title
Constraint-Aware Extraction & Formatting
## Description
Map the extracted information directly to the question's specific constraint and immediately apply the required output structure.
## Content
Parse the question to isolate the exact attribute needed (e.g., "this city" vs. full address or state). Extract only that precise element, discard extraneous details, and wrap the result strictly in the mandated tags to ensure seamless downstream processing.

# Success Memory Item 3
## Title
Direct Answer Generation
## Description
Maintain response conciseness by outputting only the validated answer without supplementary explanation or conversational filler.
## Content
After isolating the correct entity, generate the final output immediately. Avoid adding context summaries, reasoning traces, or polite phrases outside the designated answer block. This preserves token efficiency and aligns with strict evaluation metrics.
