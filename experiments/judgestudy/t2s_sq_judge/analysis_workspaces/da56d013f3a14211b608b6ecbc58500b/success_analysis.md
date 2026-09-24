# Success Memory Item 1
## Title
Clue-Style Prompt Recognition
## Description
Detect when a question is phrased as a concise trivia or quiz clue, then treat it as a set of constraints to match against retrieved context.
## Content
Questions formatted as short descriptive phrases (e.g., "[Place] that was scene of [Event] in [Media]") typically expect a single named entity. Scan context for exact or near-exact matches to these phrases, prioritizing titles, summaries, or archive entries that explicitly connect the location to the described event and media.

# Success Memory Item 2
## Title
Multi-Signal Entity Confirmation
## Description
Cross-reference multiple context snippets to ensure the candidate entity satisfies all prompt constraints before finalizing.
## Content
Confirm the selected entity aligns with every descriptor in the prompt (geographic location, nature of the event, and associated creative works). Rely on overlapping evidence across different document types (reviews, plot summaries, metadata) to confidently isolate the correct answer without guessing.

# Success Memory Item 3
## Title
Direct Entity Output Formatting
## Description
Immediately wrap the confirmed entity in the required tags, omitting all reasoning or supplementary text.
## Content
Once the exact match is identified, output strictly as `<answer>[Entity Name]</answer>`. Avoid introductory phrases, alternative options, or explanatory notes to maintain precision and comply with automated grading formats.
