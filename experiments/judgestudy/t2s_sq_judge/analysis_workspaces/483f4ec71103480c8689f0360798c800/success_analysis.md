# Success Memory Item 1
## Title
Direct Descriptor Anchoring
## Description
Locate the target entity by scanning retrieved snippets for verbatim or highly specific descriptive phrases from the prompt.
## Content
When a question contains a unique quote, epithet, or defining trait (e.g., "bear of very little brain"), prioritize exact or near-exact matches in the context. This bypasses broad semantic searches and rapidly isolates the relevant document snippet containing the answer.

# Success Memory Item 2
## Title
Creator-Entity Alignment
## Description
Confirm the candidate entity belongs to the specific author, franchise, or universe explicitly named in the prompt.
## Content
Cross-reference any stated creator or source identifier (e.g., "Milne") with the context's metadata. Ensure the identified character or object originates from that creator's catalog to rule out similarly named entities from different series or adaptations.

# Success Memory Item 3
## Title
Canonical Naming & Tag Compliance
## Description
Select the most widely recognized full name for the entity and enforce strict output formatting.
## Content
When multiple aliases or shortened forms exist, default to the complete, standard title (e.g., "Winnie-the-Pooh" instead of "Pooh"). Immediately wrap the final string in the required answer tags without additional commentary to satisfy parsing constraints.
