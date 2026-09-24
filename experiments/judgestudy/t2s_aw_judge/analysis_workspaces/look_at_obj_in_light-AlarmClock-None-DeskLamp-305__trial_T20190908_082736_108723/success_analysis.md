# Success Memory Item 1
## Title
Resolve Displaced Spatial Constraints via Relocation
## Description
When a goal specifies a positional relationship between two objects (e.g., "under"), and they are initially separate, systematically retrieve the target object and place it at the reference object's location.
## Content
Navigate to the reference object first if possible, or locate it after retrieving the target. Use `take` to acquire the target, travel to the reference, and use `move <target> to <reference>` to establish the required spatial configuration before proceeding to state changes or inspections.

# Success Memory Item 2
## Title
Preemptively Activate Required Environmental States
## Description
Visual goals containing conditional phrases like "in light" or "under a lamp" implicitly require changing the environment's state. These state changes must be executed before the final inspection step.
## Content
Parse the goal for implicit state triggers. Once the target is correctly positioned relative to the reference, interact with the relevant mechanism (e.g., `use <lamp/switch>`) to activate the condition. Failure to trigger this state change will prevent successful completion of the visual inspection.

# Success Memory Item 3
## Title
Validate Configuration Before Final Inspection
## Description
After repositioning objects and altering environmental states, verify that the physical setup matches the goal's requirements before executing the terminal observation action.
## Content
Use `examine <reference_location>` to confirm the target is present and the environmental state (e.g., light status) is active. Immediately follow verification with the terminal action (`take` or `examine` on the target) to register the successful observation and terminate the episode.
