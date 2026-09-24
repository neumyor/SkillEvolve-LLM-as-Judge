# Success Memory Item 1
## Title
Constraint Decomposition & Keyword Mapping
## Description
Dissect multi-clause questions into discrete factual attributes to create a targeted search profile for the retrieved context.
## Content
Extract specific descriptors from the prompt (e.g., physical characteristics, originating group, historical figures, and qualitative claims). Treat each descriptor as an independent filter and scan the context for explicit mentions or semantic equivalents. This ensures every part of the question is addressed before selecting a candidate.

# Success Memory Item 2
## Title
Cross-Snippet Evidence Aggregation
## Description
Synthesize fragmented information across multiple retrieved documents to fully satisfy complex query constraints.
## Content
When no single context chunk contains all necessary details, identify complementary snippets that each cover a subset of the question's attributes. Map each piece of evidence to its corresponding constraint, then combine them to verify that a single entity consistently aligns with all conditions. This prevents premature conclusions based on isolated or partial matches.

# Success Memory Item 3
## Title
Direct Entity Extraction & Structural Compliance
## Description
Output the validated answer concisely within the required formatting boundaries, eliminating extraneous commentary.
## Content
Once the target entity satisfies all mapped constraints, extract it in its standard form. Immediately place the result inside the designated response tags, bypassing narrative explanations or step-by-step summaries in the final output. This maintains precision, reduces token waste, and guarantees strict adherence to structural requirements.
