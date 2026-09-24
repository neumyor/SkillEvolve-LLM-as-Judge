# Success Memory Item 1
## Title
Decode Statement-Based Prompts as Entity Identification Tasks
## Description
Treat descriptive statements or trivia-style clues as requests to identify the underlying subject rather than literal questions.
## Content
When the input lacks an explicit interrogative structure, scan the retrieved context for matching phrases or semantic equivalents. Map the descriptive details directly to the named entity in the text to extract the target answer.

# Success Memory Item 2
## Title
Disambiguate Entities Using Specific Geographic and Thematic Markers
## Description
Filter out thematically similar but factually incorrect candidates by anchoring to precise location and activity descriptors.
## Content
Cross-reference unique identifiers in the prompt (e.g., city names, specific institutions, or campaign focuses) against all mentioned figures. Prioritize the entity that satisfies all spatial and contextual constraints while discarding those that only share peripheral themes.

# Success Memory Item 3
## Title
Isolate and Format the Final Entity Directly
## Description
Strip away contextual narrative once the target entity is confirmed, applying the required output wrapper immediately.
## Content
After mapping the prompt to the correct subject, bypass explanatory text or intermediate steps in the final output. Encapsulate only the identified name or term within the designated tags to meet strict formatting requirements and optimize for automated scoring.
