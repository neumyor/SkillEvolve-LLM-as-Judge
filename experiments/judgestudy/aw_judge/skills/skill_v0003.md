# ALFWorld Embodied Agent Skill

## Overview
This skill guides agents operating in the ALFWorld text-based embodied environment.
The agent must complete household tasks by navigating rooms, interacting with objects,
and using appliances. Actions must be chosen from the admissible action list provided
at each step.

**Output format**: Always output `<think>...</think>` for reasoning, then `<action>...</action>` for the chosen action.

---

## Task Types

| Type | Goal | Key Steps |
|------|------|-----------|
| Pick & Place | Put object X in/on receptacle Y | Find X -> take X -> go to Y -> put X in/on Y |
| Pick Two & Place | Put two instances of X in/on Y | Find X1 -> take -> place -> find X2 -> take -> place |
| Examine in Light | Examine object X under desklamp | Find X -> take X -> find desklamp -> use desklamp |
| Clean & Place | Clean object X and put in/on Y | Find X -> take X -> go to sink -> clean X -> go to Y -> put X |
| Heat & Place | Heat object X and put in/on Y | Find X -> take X -> go to microwave -> open -> move X in -> close -> heat X -> open -> take X -> go to Y -> put X |
| Cool & Place | Cool object X and put in/on Y | Find X -> take X -> go to fridge -> open -> move X in -> close -> cool X -> open -> take X -> go to Y -> put X |

---

## General Principles

1. **Decompose the task**: Parse the goal into ordered sub-goals (locate, acquire, transform, deliver). Complete each before moving to the next.
2. **Semantic & Systematic Exploration**: Begin searches at **semantically likely locations** (e.g., cutlery in drawers, produce on countertops, bedding on beds, electronics on desks/dressers). Maintain a strict mental log of every container and surface inspected. Once a specific *type* of furniture (e.g., all drawers, all cabinets) is checked and consistently yields no results, mark that entire category as **exhausted**. Immediately pivot to a different furniture category or room zone. Never revisit an empty container or type while other unexplored options remain, **except** when cycling through an appliance's operational sequence. Prioritize moving to new, unvisited areas over returning to previously checked surfaces.

**Functional Equivalent Trigger**: If the exact target object remains unfound after thoroughly checking 3-4 semantically relevant locations or exhausting one furniture category, **immediately accept a functionally equivalent item** (e.g., 'pot' for 'pan', 'cup' for 'mug', 'bowl' for 'plate'). Do not continue searching for the exact name if it causes indefinite loops. Trust that the environment accepts valid substitutes for the task's physical requirements.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform strategically**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance. However, be aware that placing an object into a fridge cools it, and into a microwave heats it. If the destination appliance would alter the object's state undesirably, perform the transformation *after* placing the object at the destination.
5. **Direct delivery & hand management**: For single-object tasks, navigate straight to the target receptacle and place it. For 'Pick Two' tasks, place the first object at the destination immediately to free your hands for searching and retrieving the second object. Do not attempt to hold multiple objects simultaneously.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Track your recent navigation history. If you find yourself cycling through the same 3+ locations without progress, **stop and reassess**. Verify your inventory, check if you are holding the target, or consider that the target may be named differently than expected. Force a change of direction to a completely unvisited room or furniture type.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.
9. **Appliance & Receptacle Workflow**: Enclosed appliances require a strict sequence: `open <appliance>` -> `move <object> in` -> `close <appliance>` -> `heat/cool/clean <object> with <appliance>` -> `open <appliance>` -> `take <object> from <appliance>`. Always verify receptacles are open before placing items. **Always close appliances** immediately after interaction and retrieval to maintain environment state. Note: Some environments allow direct commands like `heat <object> with <appliance>` without moving it in/out; attempt the direct command first if holding the object near the appliance. **Fallback Rule**: If the direct command succeeds but the object's state does not update (verify via `examine`), or if subsequent placement/interaction fails, immediately switch to the full enclosed appliance workflow (`open` -> `move in` -> `close` -> `heat/cool` -> `open` -> `take`). Do not persist with direct commands if they do not advance the task state.
10. **State Verification & Precision**: Call `inventory` whenever unsure what you hold or if expected actions are missing. Immediately confirm an object's exact name upon pickup. When multiple instances exist, always use the full admissible action string (e.g., `take X from Y`).

11. **Action-Driven Inference**: When visual observations are ambiguous or incomplete, rely on the **admissible action list** to infer your inventory status and object locations. Actions like `move <object> to <location>` or `examine <object>` appearing in the list strongly indicate you are holding that object or it exists nearby. Use this signal to guide navigation and reduce unnecessary searching.

12. **Proactive Receptacle Opening**: If the task requires placing an item into a closed container (e.g., fridge, drawer, cabinet), open it early in the workflow. Keeping it open during intermediate steps (like heating or cleaning) saves navigation steps and prevents state mismatches upon return.

13. **Strategic `look` Usage**: When an expected object is not visible in the current observation or admissible actions, execute `look` to refresh your spatial awareness. This reveals nearby items or confirms room layout without consuming navigation steps, effectively breaking search deadlocks.

14. **Sequential Numbered Furniture Search**: When encountering multiple numbered containers of the same type (e.g., `drawer 1`–`N`, `cabinet 1`–`N`), systematically check them in numerical order until the target is found or the sequence is exhausted. Do not skip numbers or guess randomly.

15. **Co-located Multi-Object Handling**: For 'Pick Two' tasks, if both target instances are found on the same surface, take the first, navigate to the destination, place it, then return to the original surface to retrieve the second. This avoids unnecessary cross-room searches when items share a location.

16. **Transformation Location Mapping**: Strictly associate task verbs with their required locations. `clean` must be performed at a `sinkbasin`; `heat` requires a `microwave` or `stoveburner`; `cool` requires a `fridge`. Placing an item in a fridge cools it but does *not* clean it. Never assume a transformation at one location satisfies a requirement for another. If the task specifies `clean`, navigate to the sink regardless of other transformations completed.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them unnecessarily.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required. Conversely, do not place an object into an appliance (like a fridge or microwave) unless intended, as this may trigger automatic cooling/heating and ruin the desired state.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.
- **Accept functional equivalents**: If the exact target object (e.g., 'pan', 'mug', 'keychain') is not found after thorough searching, consider taking functionally similar items (e.g., 'pot', 'cup', 'tag') that fulfill the task's physical requirements. Do not let strict naming conventions cause indefinite loops.
- **Verify post-appliance state**: Immediately after using a transformation appliance (microwave, fridge, sink), execute `inventory` to confirm you are holding the transformed object before navigating to the final destination. Appliance interactions may auto-transfer items or require explicit retrieval.
- **Neglecting appliance/receptacle states**: Attempting to use or store items in closed appliances causes errors. Always open microwaves, fridges, and cabinets before interacting.
- **Hoarding the first object in multi-object tasks**: Holding onto the first required item while searching for the second wastes steps. Place the first item at the destination as soon as possible to free your hands.

10. **Appliance Interaction & State Verification**: For heating/cooling tasks, use the explicit admissible command (e.g., `heat <object> with <appliance>` or `cool <object> with <appliance>`). Immediately after any appliance interaction, execute `inventory` to verify you are holding the transformed object and confirm its state before navigating to the destination. Do not assume automatic transfer or skip state checks.

## Task Completion Protocol
- **Verify Before Stopping**: When `done()` is available, call it only after explicitly verifying that the object is in the correct receptacle/surface AND meets all task conditions. Perform a final `look` or `inventory` check if unsure.
- **Handle Blocked Actions**: If placement actions are missing from the admissible list, inspect the receptacle's state or re-evaluate the object's properties. Adjust your approach rather than looping or guessing.
- **Trust Successful Placement**: If you have just placed the required object onto the target surface/receptacle and `done()` is **not** listed in the admissible actions, **do not re-pick the object**. Assume the task is complete and attempt to end the episode. Repeatedly picking up and placing down already-delivered items wastes steps and prevents termination.
