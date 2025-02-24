Build and Run
Install trunk: cargo install trunk.
Build and serve: trunk serve --open.
Open http://localhost:8080 in your browser.
How It Works:
2D Maze Replacement for Frontend Components:
Search Bar: Replaced by the player’s starting position (red square at top-left). The maze itself is the interactive “query” area—navigate to the goal instead of typing a search.
Content Area: The maze grid (black walls, white paths) replaces the result display. It’s a 20x15 grid of 40x40 pixel cells, rendered as sprites.
Control Panel: Replaced by keyboard controls (Arrow keys or WASD) to move the player. The goal (green square at bottom-right) serves as the “submit” or endpoint.
Bevy as Three.js Equivalent:
Rendering: Bevy’s 2D sprite system renders the maze, player, and goal, akin to Three.js’s scene graph but in 2D.
Camera: An orthographic 2D camera centers the maze and scales responsively using ScalingMode::AutoMin, ensuring it fits various screen sizes.
Input: Bevy’s input system handles keyboard events, replacing button clicks with player movement.
Maze Generation and Routing:
Generation: A recursive backtracking algorithm creates a solvable maze with paths and walls. The player starts at (1,1), and the goal is at (MAZE_WIDTH-2, MAZE_HEIGHT-2).
Routing: The player moves through the maze using arrow keys or WASD. The move_player system ensures movement only along valid paths (is_path check).
Goal: Reaching the green square triggers an exit event, simulating a completed “query.”
Responsiveness:
Scaling: Bevy’s camera scales the maze to fit the window while maintaining aspect ratio, adapting to phone (e.g., 375x667) and laptop (e.g., 1920x1080) resolutions.
Canvas Fit: fit_canvas_to_parent ensures the canvas fills the browser window, making it responsive by design.
Notes:
Integration: This doesn’t connect to your Twitter API backend yet. To tie it back, you could map API calls to maze generation (e.g., user ID seeds the RNG) or display API results as text overlays using Bevy’s UI system.
Enhancements: Add a reset button or UI controls using Bevy’s bevy_ui feature if you want to mimic the original control panel more closely.
Performance: Bevy compiles to WASM efficiently, but large mazes might need optimization (e.g., chunked rendering).
This transforms your frontend into a 2D maze game, leveraging Bevy as a Rust equivalent to Three.js for 2D graphics, fully in WebAssembly! Let me know if you’d like to integrate the API logic or refine the maze further.