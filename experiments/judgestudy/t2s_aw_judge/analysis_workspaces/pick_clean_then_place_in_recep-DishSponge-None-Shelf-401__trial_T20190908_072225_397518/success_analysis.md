# Success Memory Item 1
## Title
Systematic Location Scanning
## Description
Employ a breadth-first search approach across plausible storage surfaces when the target object is not immediately visible.
## Content
Begin searching at high-probability locations for the object type. If the initial spot is empty, transition to alternative containers or flat surfaces without revisiting previous failures. Maintain awareness of available navigation targets to minimize backtracking and ensure efficient discovery.

# Success Memory Item 2
## Title
Strict State-Dependent Sequencing
## Description
Enforce a rigid three-phase workflow: acquisition, processing, and placement, ensuring each phase completes before initiating the next.
## Content
Phase 1: Secure the object in inventory using a take command. Phase 2: Transport the held object to the specific tool or basin required for modification (e.g., cleaning, charging). Phase 3: Navigate to the designated storage receptacle and deposit the item. Skipping inventory acquisition or attempting out-of-order actions will fail.

# Success Memory Item 3
## Title
Receptacle-Matched Interaction Syntax
## Description
Align interaction verbs strictly with the functional role of the target surface to guarantee valid environmental transitions.
## Content
Use `take [object] from [surface]` for pickup, `clean [object] with [basin/tool]` for maintenance, and `move [object] to [storage]` for final placement. Always navigate directly to the required receptacle prior to execution, as the environment requires explicit spatial alignment for context-specific commands.
