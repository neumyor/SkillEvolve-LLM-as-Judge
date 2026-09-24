# ALFWorld Task Execution

## Plan the task
- Decompose compound objectives into a strict, prerequisite-dependent linear pipeline (e.g., locate → acquire → transform → deliver).
- Maintain an explicit inventory and task-state checklist. Verify progress via environment feedback after every action before advancing to the next phase.
- Avoid repeating action sequences that yield no new information or state changes. Pivot to unexplored areas or alternative strategies when stuck.

## Search and navigation
- Systematically exhaust all visible storage containers, surfaces, and appliances in a consistent order before concluding an object is absent. Track visited locations to prevent redundant loops.
- Prioritize high-probability storage zones based on object semantics, but expand search breadth-first across all furniture types if initial locations are empty.
- Navigate directly to target locations and receptacles once identified. Minimize intermediate stops and avoid revisiting confirmed-empty spaces.
- Limit `inventory` checks to moments of uncertainty, immediately after a successful pickup, or when transitioning between search and execution phases.

## Object manipulation
- Secure the target object in inventory using a direct `take` command before attempting any transformation, inspection, or placement.
- Align interaction verbs strictly with environmental affordances (e.g., `clean` at washing stations, `heat`/`cool` at appliances, `move`/`put` at receptacles). Verify spatial alignment before executing commands.
- Manage container and appliance states proactively: always `open` closed units before inspection or retrieval, and follow strict state-transition cycles for thermal or mechanical processing.
- Complete all required object modifications and environmental state changes (e.g., activating lighting, adjusting temperatures) before proceeding to final placement or inspection.
- For multi-object tasks, process items sequentially: pick up one object, transport and place it, confirm inventory is empty, then retrieve the next. Never attempt simultaneous possession.
