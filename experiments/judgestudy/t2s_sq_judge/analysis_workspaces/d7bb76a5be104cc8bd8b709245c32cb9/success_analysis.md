# Success Memory Item 1
## Title
Recognize Implicit Question Targets in Incomplete Prompts
## Description
Identify when a prompt is phrased as a partial statement or list and infer the actual missing element being requested, rather than treating the prompt as a literal fact-check or fill-in-the-blank.
## Content
When encountering prompts structured as "Divisions of this state's [Entity] include X, Y & Z," parse the grammar to determine the true target (e.g., the state name). Shift focus from verifying every listed item to answering the implicit question embedded in the phrasing.

# Success Memory Item 2
## Title
Map Sub-Entities to Parent Geographic Units via Co-Occurrence
## Description
Use specific subdivisions or districts mentioned in the prompt alongside a known larger entity to locate their parent administrative or geographic region within the context.
## Content
Scan the retrieved documents for explicit links between the named subdivisions (e.g., Long Cane, Enoree) and the broader entity (e.g., Sumter National Forest). When multiple passages consistently pair these subdivisions with a specific location (e.g., South Carolina), treat that location as the definitive answer regardless of minor prompt ambiguities.

# Success Memory Item 3
## Anchor on Strongest Contextual Signals Over Prompt Noise
## Description
Ignore contradictory, irrelevant, or poorly formed details in the prompt if the core entities and context overwhelmingly support a single, coherent answer.
## Content
If the prompt includes a mismatched or inaccurate detail (e.g., listing "Tiger" as a division when the context only references a creek or species), do not force alignment. Instead, prioritize the most frequently corroborated contextual evidence and proceed with the answer that best satisfies the primary intent of the query.
