# Success Memory Item 1
## Title
Multi-Constraint Context Matching for Entity Identification
## Description
Decompose the query into distinct factual anchors and systematically scan retrieved documents to locate the single entity that satisfies all constraints simultaneously.
## Content
1. Extract explicit identifiers from the question (e.g., cast members, authors, genres, source material types).
2. Cross-reference these anchors against the retrieved context, prioritizing passages where multiple identifiers co-occur.
3. Confirm the candidate entity functionally bridges all stated constraints within the same context window.
4. Output only the identified entity using the mandated formatting tags, omitting conversational filler or intermediate reasoning steps.
