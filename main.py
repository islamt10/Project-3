import asyncio
import heapq
import math
import random

import pygame

pygame.init()

# setting
FPS = 60
CELL = 36
GRID_W, GRID_H = 29, 19                
MAZE_W, MAZE_H = GRID_W * CELL, GRID_H * CELL  
WIDTH, HEIGHT = MAZE_W, MAZE_H  

prob_burger = 10
prob_potion = 5
prob_radiation = 5
prob_trap = 5

NUM_ZOMBIES = 6
MAX_HEALTH = 5
DIRECTIONS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}


COLOR_BG = (12, 34, 20)          # dark green
COLOR_WALL = (92, 98, 96)        # sewer grey
COLOR_MOSS = (64, 130, 70)       # green wall trim
COLOR_WATER = (24, 92, 88)       # turquoise water
COLOR_RIPPLE = (48, 170, 160)
COLOR_TEXT = (230, 240, 230)
COLOR_DIM = (150, 170, 155)
COLOR_YELLOW = (250, 220, 60)
COLOR_RED = (230, 70, 60)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sewer Survivors")
clock = pygame.time.Clock()

zombie_image = pygame.transform.scale(pygame.image.load("assets/zombie.png").convert_alpha(), (34, 34))
player_image = pygame.transform.scale(pygame.image.load("assets/player.png").convert_alpha(), (44, 44))
food_image = pygame.transform.scale(pygame.image.load("assets/food.png").convert_alpha(), (26, 26))
boss_image = pygame.transform.scale(pygame.image.load("assets/zombie.png").convert_alpha(), (70, 70))
boss_image.fill((120, 190, 120), special_flags=pygame.BLEND_RGB_MULT) 

def load_sprite(path, max_w, max_h):
    # crop and fit pictures
    image = pygame.image.load(path).convert_alpha()
    image = image.subsurface(image.get_bounding_rect()).copy()
    scale = min(max_w / image.get_width(), max_h / image.get_height())
    new_w = round(image.get_width() * scale)
    new_h = round(image.get_height() * scale)
    return pygame.transform.smoothscale(image, (new_w, new_h))

potion_image = load_sprite("assets/potion.png", 24, 24)
trap_image = load_sprite("assets/Trap.png", 26, 26)
ladder_image = load_sprite("assets/Ladder.png", 44, 44)

title_font = pygame.font.Font("assets/Creepster.ttf", 64)
big_font = pygame.font.Font("assets/Creepster.ttf", 38)
hud_font = pygame.font.Font("assets/Arial.ttf", 18)
small_font = pygame.font.Font("assets/Arial.ttf", 13)


# helper methds
def is_wall(x, y):
    return not (0 <= x < GRID_W and 0 <= y < GRID_H) or grid[y][x] == 1


def cell_of(pos):
    return (int(pos.x // CELL), int(pos.y // CELL))


def center(cell):
    return pygame.Vector2(cell[0] * CELL + CELL / 2, cell[1] * CELL + CELL / 2)


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def circle_hits_wall(pos, radius):
    # check circle collisoins
    cx, cy = cell_of(pos)
    for y in range(cy - 1, cy + 2):
        for x in range(cx - 1, cx + 2):
            if is_wall(x, y):
                left, top = x * CELL, y * CELL
                # Keep the circle's center inside the tile's edges
                closest_x = max(left, min(pos.x, left + CELL))
                closest_y = max(top, min(pos.y, top + CELL))
                if pos.distance_to((closest_x, closest_y)) < radius:
                    return True
    return False


def can_see(a, b, max_dist):
    # check if there is line of sight
    to_b = b - a
    dist = to_b.length()
    if dist > max_dist:
        return False
    steps = int(dist // 6) + 1
    for i in range(steps + 1):
        p = a + to_b * (i / steps)
        if is_wall(int(p.x // CELL), int(p.y // CELL)):
            return False
    return True


def astar(start, goal):
    if start == goal:
        return [start]
    frontier = [(manhattan(start, goal), 0, start)]
    came_from = {start: None}
    cost = {start: 0}
    while frontier:
        _, g, current = heapq.heappop(frontier)
        if current == goal:
            break
        for dx, dy in DIRECTIONS.values():
            nxt = (current[0] + dx, current[1] + dy)
            if is_wall(*nxt):
                continue
            new_cost = cost[current] + 1
            if nxt not in cost or new_cost < cost[nxt]:
                cost[nxt] = new_cost
                came_from[nxt] = current
                heapq.heappush(frontier, (new_cost + manhattan(nxt, goal), new_cost, nxt))
    if goal not in came_from:
        return []
    path, node = [], goal
    while node is not None:
        path.append(node)
        node = came_from[node]
    path.reverse()
    return path


# DFS maze generation
def generate_maze(w, h):
    # Initialize maze, 1 = wall, 0 = empty
    maze = [[1] * w for _ in range(h)]
    stack = [(1, h - 2)]
    maze[h - 2][1] = 0

    while stack:
        cx, cy = stack[-1]
        neighbors = []
        # Move by 2
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            nx, ny = cx + dx, cy + dy
            if 0 < nx < w - 1 and 0 < ny < h - 1 and maze[ny][nx] == 1:
                neighbors.append((nx, ny))

        if neighbors:
            nx, ny = random.choice(neighbors)
            # Carve path through the dividing wall (halfway between the two cells)
            maze[(cy + ny) // 2][(cx + nx) // 2] = 0
            maze[ny][nx] = 0
            stack.append((nx, ny))
        else:
            stack.pop()   # dead end, backtrack

    # make maze imperfect
    for i in range(w * h // 12):
        x = random.randint(1, w - 2)
        y = random.randint(1, h - 2)
        if maze[y][x] == 1:
            path_left_and_right = maze[y][x - 1] == 0 and maze[y][x + 1] == 0
            path_up_and_down = maze[y - 1][x] == 0 and maze[y + 1][x] == 0
            # Only remove walls that sit between two paths in a straight line
            if path_left_and_right != path_up_and_down:
                maze[y][x] = 0
    return maze


# player class
class Player:
    def __init__(self, position):
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(0, 0)
        self.angle = 90
        self.thrust = 0.5
        self.drag = 0.85
        self.VELOCITYMAX = 3.2
        self.radius = 11
        self.hunger = 100
        self.HUNGER_MAX = 100
        self.HUNGER_DRAIN_RATE = 2.5
        self.health = MAX_HEALTH
        self.poisoned = False
        self.stunned_until = 0
        self.boost_until = 0

    def boosted(self, now):
        return now < self.boost_until

    def stunned(self, now):
        return now < self.stunned_until

    def update(self, keys, now):
        direction = pygame.Vector2(0, 0)
        if not self.stunned(now):
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                direction.y -= 1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                direction.y += 1
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                direction.x -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                direction.x += 1
        else:
            self.velocity *= 0

        if direction.length_squared():
            direction = direction.normalize()
            self.angle = math.degrees(math.atan2(-direction.y, direction.x))
            boost = 1.6 if self.boosted(now) else 1
            self.velocity += direction * self.thrust * boost
            if self.velocity.length() > self.VELOCITYMAX * boost:
                self.velocity.scale_to_length(self.VELOCITYMAX * boost)
            # Corner assist 
            nudge = center(cell_of(self.position)) - self.position
            if direction.x != 0:
                nudge.x = 0
            if direction.y != 0:
                nudge.y = 0
            if nudge.length() > 1.5:
                nudge.scale_to_length(1.5)
            self.position += nudge
            if circle_hits_wall(self.position, self.radius):
                self.position -= nudge

        self.velocity *= self.drag
        # Make sliding along walls possible
        self.position.x += self.velocity.x
        if circle_hits_wall(self.position, self.radius):
            self.position.x -= self.velocity.x
            self.velocity.x = 0
        self.position.y += self.velocity.y
        if circle_hits_wall(self.position, self.radius):
            self.position.y -= self.velocity.y
            self.velocity.y = 0

    def draw(self, now):
        if self.stunned(now):
            pygame.draw.circle(screen, COLOR_YELLOW, self.position, self.radius + 4)
        rotated = pygame.transform.rotate(player_image, self.angle)
        screen.blit(rotated, rotated.get_rect(center=self.position))


# the items
class Item:
    def __init__(self, kind, cell):
        self.kind = kind
        self.position = center(cell)
        self.radius = 10

    def draw(self):
        x, y = self.position
        if self.kind == "burger":
            screen.blit(food_image, food_image.get_rect(center=self.position))
        elif self.kind == "potion":
            screen.blit(potion_image, potion_image.get_rect(center=self.position))
        elif self.kind == "radiation":
            pygame.draw.circle(screen, (120, 255, 60), (x, y), 10)
            pygame.draw.circle(screen, (20, 40, 10), (x, y), 3)
            for angle in (90, 210, 330):
                p = self.position + pygame.Vector2(0, -6).rotate(angle)
                pygame.draw.circle(screen, (20, 40, 10), p, 2)
        elif self.kind == "trap":
            screen.blit(trap_image, trap_image.get_rect(center=self.position))


# MarkovPredictor
class MarkovPredictor:
    def __init__(self):
        # counts[last move][next move] = how many times that happened
        self.counts = {}
        for d in DIRECTIONS:
            self.counts[d] = {"UP": 0, "DOWN": 0, "LEFT": 0, "RIGHT": 0}
        self.last = None
        self.correct = 0
        self.total = 0

    def probabilities(self, from_dir):
        row = self.counts[from_dir]
        total = sum(row.values())
        if total == 0:
            return {d: 0.25 for d in DIRECTIONS}
        return {d: row[d] / total for d in DIRECTIONS}

    def predict(self):
        # Most common next move in the row of the player's last move
        if self.last is None or sum(self.counts[self.last].values()) == 0:
            return None
        row = self.counts[self.last]
        return max(row, key=row.get)

    def record(self, direction):
        guess = self.predict()
        if guess is not None:
            self.total += 1
            self.correct += guess == direction
        if self.last is not None:
            self.counts[self.last][direction] += 1
        self.last = direction

    def candidates(self, start, steps=4):
        # Follow the most likely open direction `steps` cells ahead
        result, pos, d, prob = [], start, self.last, 1.0
        if d is None:
            return result
        for _ in range(steps):
            probs = self.probabilities(d)
            # Only directions that aren't walls are possible, so share the
            # probability out among those
            options = []
            for name, (dx, dy) in DIRECTIONS.items():
                if not is_wall(pos[0] + dx, pos[1] + dy):
                    options.append(name)
            if not options:
                break
            total = sum(probs[o] for o in options)
            if total == 0:
                probs = {o: 1 / len(options) for o in options}
            else:
                probs = {o: probs[o] / total for o in options}
            d = max(options, key=probs.get)
            prob *= probs[d]
            dx, dy = DIRECTIONS[d]
            pos = (pos[0] + dx, pos[1] + dy)
            result.append((pos, prob))
        return result


# inherited by npc classes
class Mover:
    image = zombie_image

    def __init__(self, cell):
        self.pos = center(cell)
        self.path = []
        self.angle = 0
        self.facing = pygame.Vector2(1, 0)

    def follow_path(self, speed):
        # If we're already heading from path[0] toward path[1], skip path[0]
        if len(self.path) >= 2:
            a, b = center(self.path[0]), center(self.path[1])
            if (b - a).dot(self.pos - a) > 0:
                self.path.pop(0)
        if not self.path:
            return
        to_target = center(self.path[0]) - self.pos
        if to_target.length() <= speed:
            self.pos = center(self.path[0])
            self.path.pop(0)
        else:
            self.move(to_target.normalize() * speed)

    def move(self, step):
        self.pos += step
        self.facing = step.normalize()
        self.angle = math.degrees(math.atan2(-step.y, step.x))

    def draw(self):
        rotated = pygame.transform.rotate(self.image, self.angle)
        screen.blit(rotated, rotated.get_rect(center=self.pos))


class EnemyFSM(Mover):
    SIGHT_RANGE = 8 * CELL
    FOV_DOT = math.cos(math.radians(60))
    ATTACK_RANGE = CELL
    ATTACK_COOLDOWN = 1000
    PATROL_SPEED = 1.0
    CHASE_SPEED = 1.8
    radius = 12

    def __init__(self, cell):
        super().__init__(cell)
        self.state = "PATROL"
        self.last_seen = None
        self.last_attack = 0
        self.replan_at = 0

    def update(self, player, now):
        to_player = player.position - self.pos
        dist = to_player.length()
        sees = can_see(self.pos, player.position, self.SIGHT_RANGE)

        # A patrolling zombie only notices you if you're in front of it.
        if self.state == "PATROL" and dist > 0:
            if self.facing.dot(to_player.normalize()) < self.FOV_DOT:
                sees = False
        if sees:
            self.last_seen = cell_of(player.position)

        # state transitions
        if self.state == "PATROL":
            if sees:
                self.state = "CHASE"
                self.replan_at = 0
        elif self.state == "CHASE":
            if sees and dist <= self.ATTACK_RANGE:
                self.state = "ATTACK"
            elif not sees and cell_of(self.pos) == self.last_seen:
                self.state = "PATROL"                       # lost the player
                self.path = []
        elif self.state == "ATTACK":
            if not sees or dist > self.ATTACK_RANGE * 1.5:
                self.state = "CHASE"                        # player moved away
                self.replan_at = 0

        # actions
        if self.state == "PATROL":
            if len(self.path) <= 1:
                here = cell_of(self.pos)
                nearby = [c for c in open_cells if 2 <= manhattan(c, here) <= 6]
                self.path = astar(here, random.choice(nearby))
            self.follow_path(self.PATROL_SPEED)
        elif self.state == "CHASE":
            if now >= self.replan_at:
                self.path = astar(cell_of(self.pos), self.last_seen)
                self.replan_at = now + 300
            self.follow_path(self.CHASE_SPEED)
        elif self.state == "ATTACK":
            # go straight to player
            self.path = []
            if dist > self.radius + player.radius:
                step = to_player.normalize() * self.CHASE_SPEED
                if not circle_hits_wall(self.pos + step, 6):
                    self.move(step)

# The boss zombie
class Boss(Mover):
    image = boss_image
    SPEED = 2.0
    GUARD_RADIUS = 14       # cells from its home before it gives up
    radius = 22

    def __init__(self, cell):
        super().__init__(cell)
        self.home = cell
        self.mode = "GUARD"
        self.candidates = []     # (cell, probability, utility)
        self.replan_at = 0

    def update(self, player, markov, now):
        if now >= self.replan_at:
            self.replan_at = now + 300
            player_cell, boss_cell = cell_of(player.position), cell_of(self.pos)
            self.candidates = []
            if manhattan(player_cell, self.home) > self.GUARD_RADIUS:
                self.mode, target = "GUARD", self.home
            elif self.pos.distance_to(player.position) < CELL * 2.5:
                self.mode, target = "CHASE", player_cell
            else:
                self.mode, target = "AMBUSH", player_cell
                best_utility = None
                for cell, prob in markov.candidates(player_cell):
                    distance = len(astar(boss_cell, cell)) - 1
                    utility = 20 * prob - 1 * distance
                    self.candidates.append((cell, prob, utility))
                    # Go to the cell with the highest utility
                    if best_utility is None or utility > best_utility:
                        best_utility, target = utility, cell
            self.path = astar(boss_cell, target)
        self.follow_path(self.SPEED)

# game
def reset_game():
    global grid, open_cells, maze_surface, player, items, zombies, boss
    global exit_cell, start_cell, player_cell, game_over, won, message

    grid = generate_maze(GRID_W, GRID_H)
    open_cells = [(x, y) for y in range(GRID_H) for x in range(GRID_W) if grid[y][x] == 0]
    start_cell = (1, GRID_H - 2)        # bottom-left manhole
    exit_cell = (GRID_W - 2, 1)         # top-right ladder
    player = Player(center(start_cell))
    player_cell = start_cell
    markov.last = None

    # Boss guards the route a few steps in front of the exit
    route = astar(exit_cell, start_cell)
    boss = Boss(route[5])

    items = []
    for cell in open_cells:
        if manhattan(cell, start_cell) < 3 or cell in (exit_cell, boss.home):
            continue
        roll = random.uniform(0, 100)
        if roll < prob_burger:
            items.append(Item("burger", cell))
        elif roll < prob_burger + prob_potion:
            items.append(Item("potion", cell))
        elif roll < prob_burger + prob_potion + prob_radiation:
            items.append(Item("radiation", cell))
        elif roll < prob_burger + prob_potion + prob_radiation + prob_trap:
            items.append(Item("trap", cell))

    spots = [c for c in open_cells if manhattan(c, start_cell) > 10 and manhattan(c, boss.home) > 5]
    zombies = [EnemyFSM(c) for c in random.sample(spots, NUM_ZOMBIES)]

    maze_surface = draw_maze()
    game_over, won, message = False, False, ""


def draw_maze():
    # The maze never changes during a round, so draw it once onto a surface
    surface = pygame.Surface((MAZE_W, MAZE_H))
    for y in range(GRID_H):
        for x in range(GRID_W):
            rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
            if grid[y][x] == 1:
                pygame.draw.rect(surface, COLOR_WALL, rect)
                if y + 1 < GRID_H and grid[y + 1][x] == 0:
                    pygame.draw.rect(surface, COLOR_MOSS, (rect.x, rect.bottom - 5, CELL, 5))
            else:
                pygame.draw.rect(surface, COLOR_WATER, rect)
                if (x * 7 + y * 3) % 5 == 0:
                    start = (rect.x + 8, rect.centery)
                    end = (rect.x + 20, rect.centery)
                    pygame.draw.line(surface, COLOR_RIPPLE, start, end, 2)
    pygame.draw.circle(surface, (60, 60, 60), center(start_cell), CELL // 2 - 3)
    pygame.draw.circle(surface, (120, 120, 120), center(start_cell), CELL // 2 - 3, 3)
    surface.blit(ladder_image, ladder_image.get_rect(center=center(exit_cell)))
    return surface


def update_game(keys, now, delta_time):
    global player_cell, game_over, won, message
    player.update(keys, now)

    # Markov: record a move each time the player enters a new cell
    cell = cell_of(player.position)
    if cell != player_cell:
        dx, dy = cell[0] - player_cell[0], cell[1] - player_cell[1]
        if abs(dx) >= abs(dy):
            markov.record("RIGHT" if dx > 0 else "LEFT")
        else:
            markov.record("DOWN" if dy > 0 else "UP")
        player_cell = cell

    # Item pickups
    for item in items[:]:
        if player.position.distance_to(item.position) < player.radius + item.radius:
            if item.kind == "burger":
                player.hunger = min(player.HUNGER_MAX, player.hunger + 35)
                player.poisoned = False
            elif item.kind == "potion":
                player.boost_until = max(now, player.boost_until) + 5000
            elif player.boosted(now):
                continue                                   # immune to hazards
            elif item.kind == "radiation":
                player.poisoned = True
                player.health -= 1
            elif item.kind == "trap":
                player.stunned_until = now + 1500
            items.remove(item)

    drain = player.HUNGER_DRAIN_RATE * (2.5 if player.poisoned else 1)
    player.hunger = max(0, player.hunger - drain * delta_time)

    for zombie in zombies:
        zombie.update(player, now)
        touching = zombie.pos.distance_to(player.position) <= player.radius + zombie.radius + 2
        if zombie.state == "ATTACK" and touching and now - zombie.last_attack >= zombie.ATTACK_COOLDOWN:
            player.health -= 1
            zombie.last_attack = now
            zombie.state = "CHASE"  # back off after a hit
    boss.update(player, markov, now)

    # Win lose
    if boss.pos.distance_to(player.position) < boss.radius + player.radius:
        game_over, message = True, "The boss zombie caught you!"
    elif player.health <= 0:
        game_over, message = True, "You were overwhelmed!"
    elif player.hunger <= 0:
        game_over, message = True, "You starved in the sewer!"
    elif player.position.distance_to(center(exit_cell)) < CELL / 2:
        game_over, won, message = True, True, "You escaped the sewer!"

# draw
def draw_debug_world():
    for zombie in zombies:
        # vision cone
        if zombie.state == "PATROL":
            for side in (-60, 60):
                edge = zombie.facing.rotate(side) * CELL * 2
                pygame.draw.line(screen, (120, 200, 255), zombie.pos, zombie.pos + edge, 1)
        if zombie.path:
            color = (255, 140, 0) if zombie.state == "CHASE" else (200, 200, 200)
            pygame.draw.lines(screen, color, False, [zombie.pos] + [center(c) for c in zombie.path], 2)
    highlight = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
    highlight.fill((255, 230, 0, 110))
    for cell, prob, utility in boss.candidates:
        screen.blit(highlight, (cell[0] * CELL, cell[1] * CELL))
        label = small_font.render(f"{prob:.2f}", True, (0, 0, 0))
        screen.blit(label, (cell[0] * CELL + 4, cell[1] * CELL + 12))
    if boss.path:
        pygame.draw.lines(screen, (255, 80, 200), False, [boss.pos] + [center(c) for c in boss.path], 3)


def draw_debug_labels():
    for zombie in zombies:
        label = small_font.render(zombie.state, True, COLOR_TEXT)
        rect = label.get_rect(midbottom=(zombie.pos.x, zombie.pos.y - 18))
        pygame.draw.rect(screen, (0, 0, 0), rect.inflate(4, 2))
        screen.blit(label, rect)
    label = small_font.render(f"BOSS: {boss.mode}", True, COLOR_YELLOW)
    screen.blit(label, label.get_rect(midbottom=(boss.pos.x, boss.pos.y - 36)))


def draw_hud(now):
    band = pygame.Surface((WIDTH, CELL), pygame.SRCALPHA)
    band.fill((0, 0, 0, 140))
    screen.blit(band, (0, 0))

    # Top row: health, hunger, status
    x, y = 12, 9
    for i in range(MAX_HEALTH):
        pygame.draw.rect(screen, COLOR_RED if i < player.health else (70, 40, 40),
                         (x + i * 24, y, 18, 18))
    x += MAX_HEALTH * 24 + 16
    screen.blit(hud_font.render("Hunger", True, COLOR_TEXT), (x, y))
    x += 70
    hunger_color = (50, 220, 50) if player.hunger > 30 else (255, 70, 70)
    if player.poisoned:
        hunger_color = (170, 255, 60)
    pygame.draw.rect(screen, (80, 80, 80), (x, y, 200, 18))
    pygame.draw.rect(screen, hunger_color, (x, y, int(200 * player.hunger / player.HUNGER_MAX), 18))
    x += 216
    status = []
    if player.poisoned:
        status.append("POISONED")
    if player.boosted(now):
        status.append(f"BOOST {(player.boost_until - now) / 1000:.1f}s")
    if player.stunned(now):
        status.append("STUNNED")
    screen.blit(hud_font.render("  ".join(status), True, COLOR_YELLOW), (x, y))

    # status floats above the player
    if player.stunned(now) or player.boosted(now):
        label = small_font.render("STUNNED" if player.stunned(now) else "BOOST", True, COLOR_YELLOW)
        screen.blit(label, label.get_rect(midbottom=(player.position.x, player.position.y - 20)))

    if debug:
        draw_debug_panel()

def draw_debug_panel():
    accuracy = 0
    if markov.total > 0:
        accuracy = markov.correct / markov.total * 100

    lines = [(["-- AI DEBUG (F1) --"], COLOR_YELLOW),
             ([f"FPS: {clock.get_fps():.0f}"], COLOR_TEXT),
             ([f"Player cell: {cell_of(player.position)}"], COLOR_TEXT),
             ([f"Markov accuracy: {accuracy:.0f}%  ({markov.correct}/{markov.total})"], COLOR_TEXT),
             ([f"Next move guess: {markov.predict()}   Boss: {boss.mode}"], COLOR_TEXT),
             (["from\\to", "U", "D", "L", "R"], COLOR_DIM)]
    for from_dir in DIRECTIONS:
        p = markov.probabilities(from_dir)
        row = [from_dir]
        for to_dir in DIRECTIONS:
            row.append(f"{p[to_dir]:.2f}")
        color = COLOR_YELLOW if from_dir == markov.last else COLOR_TEXT
        lines.append((row, color))
    for cell, prob, utility in boss.candidates:
        lines.append(([f"candidate {cell}  p={prob:.2f}  U={utility:.1f}"], COLOR_DIM))

    panel = pygame.Surface((270, 16 + 18 * len(lines)), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 170))
    for i, (columns, color) in enumerate(lines):
        for j, text in enumerate(columns):
            panel.blit(small_font.render(text, True, color), (10 + 50 * j, 8 + 18 * i))
    x = WIDTH - panel.get_width() - 10 if player.position.x < WIDTH / 2 else 10
    screen.blit(panel, (x, CELL + 6))


def draw_centered(lines):
    # Render first so the box can fit the real text heights
    surfs = [font.render(text, True, color) for text, font, color in lines]
    text_height = sum(s.get_height() for s in surfs) + 16 * (len(surfs) - 1)
    box = pygame.Surface((MAZE_W - 200, text_height + 80), pygame.SRCALPHA)
    box.fill((0, 0, 0, 200))
    box_rect = box.get_rect(center=(MAZE_W / 2, MAZE_H / 2))
    screen.blit(box, box_rect)
    y = box_rect.y + 40
    for surf in surfs:
        screen.blit(surf, surf.get_rect(midtop=(MAZE_W / 2, y)))
        y += surf.get_height() + 16


# main
markov = MarkovPredictor()       # kept between restarts, so the boss keeps learning
debug = False


async def main():
    global debug
    reset_game()
    intro_screen = True
    r_held_since = None

    running = True
    while running:
        delta_time = clock.tick(FPS) / 1000
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F1:
                    debug = not debug
                elif intro_screen and event.key == pygame.K_SPACE:
                    intro_screen = False

        keys = pygame.key.get_pressed()

        # hold r restart
        if keys[pygame.K_r] and not intro_screen:
            if r_held_since is None:
                r_held_since = now
            elif now - r_held_since >= 100:
                reset_game()
                r_held_since = None
        else:
            r_held_since = None

        if not intro_screen and not game_over:
            update_game(keys, now, delta_time)

        # draw
        screen.fill(COLOR_BG)
        screen.blit(maze_surface, (0, 0))
        for item in items:
            item.draw()
        if debug:
            draw_debug_world()
        for zombie in zombies:
            zombie.draw()
        boss.draw()
        player.draw(now)
        if debug:
            draw_debug_labels()
        draw_hud(now)

        if intro_screen:
            draw_centered([("SEWER SURVIVORS", title_font, (140, 230, 140)),
                           ("You escaped the zombies through a manhole...", hud_font, COLOR_TEXT),
                           ("now find your way out of the sewer!", hud_font, COLOR_TEXT),
                           ("Press SPACE to continue", big_font, COLOR_YELLOW)])
        elif game_over:
            if won:
                title, title_color = "YOU ESCAPED!", (140, 230, 140)
            else:
                title, title_color = "GAME OVER", (255, 80, 80)
            draw_centered([(title, title_font, title_color),
                           (message, big_font, COLOR_TEXT),
                           ("Hold R to restart", hud_font, COLOR_DIM)])

        pygame.display.flip()
        await asyncio.sleep(0)
    pygame.quit()

asyncio.run(main())