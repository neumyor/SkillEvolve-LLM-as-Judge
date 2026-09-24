# Success Memory Item 1
## Title
Independent Location of Target and Light Source
## Description
Decompose dual-object examination tasks by separately identifying and navigating to the target item and the required light source.
## Content
Parse initial room observations and furniture inventories to pinpoint both objects. If either item is missing from the immediate vicinity, systematically search high-probability storage surfaces (e.g., desks, shelves, nightstands) until both are located.

# Success Memory Item 2
## Title
Acquire Target Before Light Interaction
## Description
Prioritize picking up the examination target over navigating to the light source to maintain correct agent state and simplify subsequent actions.
## Content
Immediately execute `take [target] from [location]` upon discovery. Securing the object in inventory first prevents navigation delays and ensures the environment recognizes the agent is holding the item when the light is activated.

# Success Memory Item 3
## Title
Direct Navigation and Activation Sequence
## Description
Once the target is secured, travel directly to the light source and trigger its activation to finalize the examination.
## Content
Move to the furniture containing the light source. Use the `use [light_source]` command to turn it on. In this task paradigm, activating the light while holding the target automatically satisfies the examination condition.
