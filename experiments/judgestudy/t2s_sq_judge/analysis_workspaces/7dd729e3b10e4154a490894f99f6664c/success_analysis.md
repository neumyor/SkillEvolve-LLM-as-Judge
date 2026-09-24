# Success Memory Item 1
## Title
Resolve Implicit Query Intent
## Description
Infer the requested target category when prompts use descriptive statements or rhetorical cues instead of direct interrogatives.
## Content
Treat actor names, specific actions, and setting details as clustered search signals. Identify the implied question type (typically a title, name, or factual identifier) upfront to direct context scanning efficiently and avoid unnecessary elaboration.

# Success Memory Item 2
## Title
Anchor Matching via Distinctive Clusters
## Description
Use highly specific contextual combinations to isolate the correct entity among scattered or tangential mentions.
## Content
Filter retrieved documents by requiring all key identifiers (e.g., both performers + the exact scene/action) to co-occur. Disregard snippets that share isolated keywords but lack the complete descriptive cluster, ensuring precise entity alignment.

# Success Memory Item 3
## Title
Extract Canonical Entity Strings
## Description
Return only the exact, unmodified name or title without supplementary phrasing or qualifiers.
## Content
Strip dates, editorial commentary, and surrounding narrative from the matched context snippet. Output the clean proper noun or title directly to maintain precision and comply strictly with formatting constraints.
