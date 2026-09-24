# Failure Cause Item 1
## Title
Rigid semantic matching caused exhaustive search loop
## Description
The agent strictly searched for an object literally named "pan" and ignored "pot 1" already visible on stoveburner 1, which is functionally equivalent. This led to 50 wasted steps cycling through cabinets, drawers, and countertops without recognizing the available target.
## Content
At step 7, the agent arrived at stoveburner 1 and saw pot 1 but continued searching elsewhere, treating "pot" and "pan" as distinct. Only at step 12 did it finally take pot 1, but then it repeatedly cycled through pick-cool-place-examine-inventory loops (steps 16-50) without recognizing the task was complete after each successful placement. The root cause is failure to map the task's generic term "pan" to the available object "pot" and failure to detect task completion after the core sequence succeeded.

# Failure Memory Item 1
## Title
Treat semantically similar objects as interchangeable for task targets
## Description
When a task specifies an item type like "pan," consider functionally equivalent objects (e.g., "pot") already present in the environment as valid targets rather than continuing an exhaustive search.
## Content
In pick_cool_then_place_in_recep tasks, the target object name in the task description may use a generic or synonym term. If a visually similar or functionally equivalent object is already located at a relevant position (e.g., a pot on a stoveburner when a pan is requested), the agent should treat it as the target and proceed with the required actions instead of searching further.

# Failure Memory Item 2
## Title
Detect task completion after core action sequence succeeds
## Description
After successfully executing the pick-cool-place sequence, recognize that the task goal is satisfied and terminate rather than re-verifying or repeating the cycle.
## Content
Once the agent has picked up an object, cooled it, and placed it on the target receptacle, the task is complete. Additional verification steps (examine, inventory, look) or repeating the pick-cool-place cycle do not contribute to goal achievement and waste steps. The agent should stop after the final placement action.

ACTION: TASK_COMPLETE
