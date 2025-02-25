use bevy::prelude::*;
use bevy::render::camera::ScalingMode;
use rand::Rng;
use wasm_bindgen::prelude::*;

// Maze constants
const CELL_SIZE: f32 = 40.0;
const MAZE_WIDTH: usize = 20;
const MAZE_HEIGHT: usize = 15;

// Colors
const WALL_COLOR: Color = Color::BLACK;
const PATH_COLOR: Color = Color::WHITE;
const PLAYER_COLOR: Color = Color::RED;
const GOAL_COLOR: Color = Color::GREEN;

// Maze cell representation
#[derive(Clone, Copy, PartialEq)]
enum Cell {
    Wall,
    Path,
}

// Player component
#[derive(Component)]
struct Player;

#[derive(Component)]
struct Goal;

// Main app setup
fn main() {
    App::new()
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "X Maze Client".into(),
                resolution: (800.0, 600.0).into(),
                fit_canvas_to_parent: true,
                ..default()
            }),
            ..default()
        }))
        .insert_resource(MazeGrid::new(MAZE_WIDTH, MAZE_HEIGHT))
        .add_systems(Startup, setup)
        .add_systems(Update, (move_player, check_goal))
        .run();
}

// Maze grid resource
#[derive(Resource)]
struct MazeGrid {
    grid: Vec<Vec<Cell>>,
}

impl MazeGrid {
    fn new(width: usize, height: usize) -> Self {
        let mut grid = vec![vec![Cell::Wall; width]; height];
        generate_maze(&mut grid, width, height);
        MazeGrid { grid }
    }

    fn is_path(&self, x: i32, y: i32) -> bool {
        x >= 0
            && y >= 0
            && (x as usize) < MAZE_WIDTH
            && (y as usize) < MAZE_HEIGHT
            && self.grid[y as usize][x as usize] == Cell::Path
    }
}

// Generate a simple maze using recursive backtracking
fn generate_maze(grid: &mut Vec<Vec<Cell>>, width: usize, height: usize) {
    let mut rng = rand::thread_rng();
    let start_x = 1;
    let start_y = 1;
    grid[start_y][start_x] = Cell::Path;

    let mut stack = vec![(start_x, start_y)];
    while let Some((x, y)) = stack.pop() {
        let directions = [
            (0, -2, 0, -1), // Up
            (0, 2, 0, 1),   // Down
            (-2, 0, -1, 0), // Left
            (2, 0, 1, 0),   // Right
        ];
        let mut neighbors = Vec::new();

        for &(dx, dy, wall_dx, wall_dy) in &directions {
            let new_x = (x as i32 + dx) as usize;
            let new_y = (y as i32 + dy) as usize;
            if new_x > 0
                && new_x < width - 1
                && new_y > 0
                && new_y < height - 1
                && grid[new_y][new_x] == Cell::Wall
            {
                neighbors.push((
                    new_x,
                    new_y,
                    (x as i32 + wall_dx) as usize,
                    (y as i32 + wall_dy) as usize,
                ));
            }
        }

        if !neighbors.is_empty() {
            stack.push((x, y));
            let (next_x, next_y, wall_x, wall_y) = neighbors[rng.gen_range(0..neighbors.len())];
            grid[next_y][next_x] = Cell::Path;
            grid[wall_y][wall_x] = Cell::Path;
            stack.push((next_x, next_y));
        }
    }

    // Set goal at bottom-right
    grid[height - 2][width - 2] = Cell::Path;
}

// Setup the maze, player, and goal
fn setup(mut commands: Commands, maze: Res<MazeGrid>) {
    // 2D Orthographic Camera
    commands.spawn(Camera2dBundle {
        projection: OrthographicProjection {
            scaling_mode: ScalingMode::AutoMin {
                min_width: MAZE_WIDTH as f32 * CELL_SIZE,
                min_height: MAZE_HEIGHT as f32 * CELL_SIZE,
            },
            ..default()
        },
        transform: Transform::from_xyz(
            (MAZE_WIDTH as f32 * CELL_SIZE) / 2.0,
            (MAZE_HEIGHT as f32 * CELL_SIZE) / 2.0,
            1000.0,
        ),
        ..default()
    });

    // Spawn maze cells
    for y in 0..MAZE_HEIGHT {
        for x in 0..MAZE_WIDTH {
            let color = match maze.grid[y][x] {
                Cell::Wall => WALL_COLOR,
                Cell::Path => PATH_COLOR,
            };
            commands.spawn(SpriteBundle {
                sprite: Sprite {
                    color,
                    custom_size: Some(Vec2::new(CELL_SIZE, CELL_SIZE)),
                    ..default()
                },
                transform: Transform::from_xyz(
                    x as f32 * CELL_SIZE,
                    (MAZE_HEIGHT - y - 1) as f32 * CELL_SIZE,
                    0.0,
                ),
                ..default()
            });
        }
    }

    // Spawn player at start (1, 1)
    commands.spawn((
        SpriteBundle {
            sprite: Sprite {
                color: PLAYER_COLOR,
                custom_size: Some(Vec2::new(CELL_SIZE, CELL_SIZE)),
                ..default()
            },
            transform: Transform::from_xyz(CELL_SIZE, (MAZE_HEIGHT - 2) as f32 * CELL_SIZE, 1.0),
            ..default()
        },
        Player,
    ));

    // Spawn goal at bottom-right
    commands.spawn((
        SpriteBundle {
            sprite: Sprite {
                color: GOAL_COLOR,
                custom_size: Some(Vec2::new(CELL_SIZE, CELL_SIZE)),
                ..default()
            },
            transform: Transform::from_xyz((MAZE_WIDTH - 2) as f32 * CELL_SIZE, CELL_SIZE, 1.0),
            ..default()
        },
        Goal,
    ));
}

// Player movement system
fn move_player(
    keyboard_input: Res<ButtonInput<KeyCode>>,
    mut player_query: Query<&mut Transform, With<Player>>,
    maze: Res<MazeGrid>,
) {
    let mut transform = player_query.single_mut();
    let (x, y) = (
        (transform.translation.x / CELL_SIZE).round() as i32,
        (MAZE_HEIGHT as f32 - 1.0 - transform.translation.y / CELL_SIZE).round() as i32,
    );

    let new_pos = if keyboard_input.just_pressed(KeyCode::ArrowUp)
        || keyboard_input.just_pressed(KeyCode::KeyW)
    {
        (x, y - 1)
    } else if keyboard_input.just_pressed(KeyCode::ArrowDown)
        || keyboard_input.just_pressed(KeyCode::KeyS)
    {
        (x, y + 1)
    } else if keyboard_input.just_pressed(KeyCode::ArrowLeft)
        || keyboard_input.just_pressed(KeyCode::KeyA)
    {
        (x - 1, y)
    } else if keyboard_input.just_pressed(KeyCode::ArrowRight)
        || keyboard_input.just_pressed(KeyCode::KeyD)
    {
        (x + 1, y)
    } else {
        return;
    };

    if maze.is_path(new_pos.0, new_pos.1) {
        transform.translation.x = new_pos.0 as f32 * CELL_SIZE;
        transform.translation.y = (MAZE_HEIGHT as i32 - new_pos.1 - 1) as f32 * CELL_SIZE;
    }
}

// Check if player reached the goal
fn check_goal(
    player_query: Query<&Transform, With<Player>>,
    goal_query: Query<&Transform, With<Goal>>,
    mut app_exit: EventWriter<AppExit>,
) {
    let player_transform = player_query.single();
    let goal_transform = goal_query.single();
    if player_transform.translation.x == goal_transform.translation.x
        && player_transform.translation.y == goal_transform.translation.y
    {
        info!("Goal reached! Exiting...");
        app_exit.send(AppExit::Success);
    }
}

// WASM entry point
#[wasm_bindgen(start)]
pub fn run_app() -> Result<(), JsValue> {
    main();
    Ok(())
}
