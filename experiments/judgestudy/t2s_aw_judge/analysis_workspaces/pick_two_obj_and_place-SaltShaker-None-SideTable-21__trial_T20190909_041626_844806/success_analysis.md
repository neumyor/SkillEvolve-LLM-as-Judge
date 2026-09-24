# Success Memory Item 1
## Title
Sequential Multi-Object Processing
## Description
Decompose multi-object placement tasks into individual pick-and-place cycles, as agents typically cannot carry or manipulate multiple items simultaneously.
## Content
Identify all target objects at their source location, then iterate through them one by one: pick up the first item, navigate to the destination, place it, return to the source for the next item, and repeat until the required quantity is fulfilled. This prevents inventory overflow errors and ensures reliable completion tracking.

# Success Memory Item 2
## Title
Optimized Source-Destination Looping
## Description
Minize navigation overhead by establishing a direct往返 pattern between the initial search location and the target receptacle.
## Content
After locating the required objects, travel directly to the destination to place the first item. Only return to the source location when explicitly needed to retrieve the next object. Avoid visiting intermediate rooms or unrelated surfaces unless they contain additional targets, keeping movement paths tight and purpose-driven.

# Success Memory Item 3
## Title
Persistent Container State Management
## Description
Maintain open states for containers holding multiple target objects to streamline subsequent retrievals without redundant interaction costs.
## Content
Once a container revealing multiple required items is opened, leave it open during return trips. This allows immediate access to remaining objects upon arrival, eliminates repeated open/close action penalties, and reduces the risk of accidentally blocking future pickups by closing the container prematurely.
