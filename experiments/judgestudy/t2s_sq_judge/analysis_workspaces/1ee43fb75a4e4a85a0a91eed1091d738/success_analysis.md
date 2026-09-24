# Success Memory Item 1
## Title
Constraint Decomposition for Targeted Scanning
## Description
Translate multi-clue prompts into discrete factual filters to guide efficient context review.
## Content
Extract explicit identifiers such as political affiliation, geographic location, official titles, years, and numerical metrics. Use these as direct lookup criteria to quickly locate matching passages within the provided documents, filtering out irrelevant information and narrowing the search space.

# Success Memory Item 2
## Title
Cross-Source Consensus Validation
## Description
Leverage repetition across multiple retrieved documents to confirm entity identity.
## Content
When several independent context passages consistently link the same named entity to all extracted constraints, treat this convergence as sufficient evidence. Prioritize the repeatedly mentioned entity over single-source mentions or ambiguous alternatives, using textual agreement as a reliability signal.

# Success Memory Item 3
## Title
Direct Entity-to-Format Mapping
## Description
Convert confirmed entities directly into the required output structure without supplementary explanation.
## Content
Once the target entity is isolated through constraint matching and consensus, output only the precise name or value inside the designated tags. Avoid hedging, listing alternatives, or adding contextual prose to maintain strict compliance and maximize scoring potential.
