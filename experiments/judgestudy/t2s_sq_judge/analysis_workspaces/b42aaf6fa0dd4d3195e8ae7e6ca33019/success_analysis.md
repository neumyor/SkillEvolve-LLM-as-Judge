# Success Memory Item 1
## Title
Entity-Context Alignment
## Description
Systematically extract key identifiers from the prompt and locate their direct counterparts in the retrieved documents to isolate the target concept.
## Content
Parse the question for specific names, dates, locations, and roles. Scan context passages for overlapping terms or explicit statements linking these elements to a single answer. Prioritize passages that directly connect multiple prompt entities, as they typically contain the precise information needed to resolve the query.

# Success Memory Item 2
## Title
Constraint Satisfaction & Alias Handling
## Description
Ensure the candidate answer aligns with all prompt conditions while resolving naming variations and descriptive equivalents.
## Content
Cross-check temporal, spatial, and role-based details against the context. Recognize equivalent terms, such as alternate name spellings, transliterations, or route descriptions that define standard events. Filter out mismatches that contradict specific constraints or misalign with the described outcome before finalizing the selection.

# Success Memory Item 3
## Title
Decoupled Output Generation
## Description
Separate analytical reasoning from the final response structure to guarantee strict compliance with output specifications.
## Content
After confirming the correct answer internally, isolate the exact term or phrase. Apply the required wrapper tags immediately, ensuring no conversational filler, step-by-step explanations, or alternative options appear in the final output block. Maintain a clean boundary between internal processing and external delivery.
