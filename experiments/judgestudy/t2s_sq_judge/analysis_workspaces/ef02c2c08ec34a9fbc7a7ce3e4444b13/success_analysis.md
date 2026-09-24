# Success Memory Item 1
## Title
Cross-Reference Specific Identifiers with Contextual Claims
## Description
Map precise question parameters (author, year, theme) directly to explicit contextual statements to isolate the target entity.
## Content
When a query contains distinct factual anchors, scan the retrieved passages for sentences that explicitly pair those anchors with a proper noun or title. Treat the paired entity as the primary candidate and verify it satisfies all stated constraints before extraction.

# Success Memory Item 2
## Title
Prioritize Verbatim Overlap for Rapid Extraction
## Description
Use exact or near-exact phrasing matches between the prompt and context snippets to shortcut the reasoning process.
## Content
If a retrieved passage closely mirrors the question's wording or clue structure, treat it as a direct pointer. Locate the missing term that completes the mirrored statement and extract it immediately, bypassing complex inference chains.

# Success Memory Item 3
## Title
Enforce Strict Delimiter Formatting Post-Extraction
## Description
Isolate the final extracted entity within the required output tags, stripping all intermediate reasoning or supplementary text.
## Content
After confirming the answer, discard all explanatory steps and place only the exact entity string inside the specified delimiters. Validate that the output contains zero extra characters or conversational filler to meet strict formatting constraints.
