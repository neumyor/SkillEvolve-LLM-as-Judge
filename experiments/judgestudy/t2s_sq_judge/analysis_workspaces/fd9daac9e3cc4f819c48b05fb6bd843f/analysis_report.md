# Failure Cause Item 1
## Title
Misinterpreting "Caustic Acid" Constraint and Ignoring Explicit Context
## Description
The agent incorrectly selected "Caustic soda" (a base) instead of "hydrochloric acid" (an acid). It prioritized the common industrial term "caustic cleaning" over the question's explicit request for an "acid" and overlooked the context passages that directly name hydrochloric acid as the substance used to clean iron/steel (remove mill scale) prior to galvanizing.
## Content
The question asks for a "very caustic acid." The agent reasoned that "caustic" implies a base like sodium hydroxide and treated the word "acid" as a potential trick or misnomer. Consequently, it ignored the context snippets stating that products are dipped in "dilute solution of hydrochloric acid" or that "ambient hydrochloric acid removes mill scale" before galvanizing. The agent failed to align the answer with the explicit entity type ("acid") requested in the prompt and the direct textual evidence provided.

# Failure Memory Item 1
## Title
Adhering to Strict Entity Type Constraints
## Description
When a question specifies a particular entity type (e.g., "acid," "metal," "element"), the correct answer must match that type. Agents should not dismiss the type constraint as a "trick" or "misnomer" if a valid candidate of that type exists in the context.
## Content
In this case, the question asked for an "acid." While "caustic soda" is chemically a base, "hydrochloric acid" is an acid and is explicitly supported by the text. Agents must verify that their chosen answer satisfies all categorical constraints in the prompt, even if the surrounding adjectives (like "caustic") seem contradictory or colloquial.

# Failure Memory Item 2
## Title
Prioritizing Explicit Context Evidence Over External Assumptions
## Description
Agents should trust explicit statements in the retrieved context over general domain knowledge when there is a conflict or ambiguity. If the text names a specific chemical or process relevant to the query, it should be preferred.
## Content
The retrieved context explicitly linked hydrochloric acid to the pre-galvanizing cleaning step (removing mill scale). The agent bypassed this direct evidence in favor of its internal knowledge about "caustic soda" being used for degreasing. This highlights the need to ground answers strictly in the provided text, especially when the text contains specific factual claims that resolve the query.

ACTION: TASK_COMPLETE
