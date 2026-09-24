# Success Memory Item 1
## Title
Constraint-Driven Entity Filtering
## Description
Systematically extract candidate entities from retrieved context and filter them against explicit question constraints to eliminate distractors before final selection.
## Content
Scan all provided documents for proper nouns or phrases matching the target category. Cross-reference each candidate against specific constraints in the prompt (e.g., time period, role, geographic association, or institutional link). Discard matches that fail any constraint early in the process to narrow the search space and prevent distraction by tangentially related terms.

# Success Memory Item 2
## Title
Contextual Cue Synthesis for Implicit Answers
## Description
When direct phrasing is absent, leverage thematic keywords and historical associations within the context to infer the most likely answer.
## Content
Identify fragmented mentions of relevant concepts, actions, or events tied to the target location or subject. Map these cues to established domain knowledge to bridge gaps between sparse context and the question's premise. Prioritize candidates strongly supported by multiple contextual threads or central to the topic's narrative over isolated or weakly connected mentions.

# Success Memory Item 3
## Title
Explicit Candidate Comparison & Justification
## Description
Evaluate top candidates side-by-side against the prompt requirements, documenting why alternatives are rejected and why the final choice fits best.
## Content
List remaining plausible options after initial filtering. For each, assess alignment with the question's specific wording and contextual evidence. Articulate clear reasoning for discarding weaker candidates and confirm the strongest match before generating the final answer. This structured comparison reduces guesswork, ensures traceable logic, and increases confidence in ambiguous retrieval scenarios.
