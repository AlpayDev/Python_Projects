"""
Level World: A turn-based roguelike using Pygame
Classes: Warrior, Rogue, Mage
Stats: HP, Attack, Defense, Speed
Map: Rectangular rooms + corridors
Monsters: Goblins, Skeletons, Rats, Bats, Ghosts
Inventory: infinite slots, loot drops
Combat: hit chance, damage rolls, XP per kill, 5 stat points on level up
"""
import pygame
import random

# === Game Settings ===
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 32
MAP_WIDTH = 40
MAP_HEIGHT = 30
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 8

# === Colors ===
COLOR_DARK_WALL = (0, 0, 100)
COLOR_DARK_FLOOR = (50, 50, 150)
COLOR_LIGHT_WALL = (130, 110, 50)
COLOR_LIGHT_FLOOR = (200, 180, 50)

# === Tile ===
class Tile:
    def __init__(self, blocked, block_sight=None):
        self.blocked = blocked
        # By default, if a tile is blocked, it also blocks sight
        self.block_sight = blocked if block_sight is None else block_sight
        self.explored = False

# === Item ===
class Item:
    def __init__(self, x, y, name, char, color, effect=None):
        self.x = x
        self.y = y
        self.name = name
        self.char = char
        self.color = color
        self.effect = effect

# === Rectangular Room ===
class Rect:
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2

    def intersect(self, other):
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

# === Actor Base Class ===
class Actor:
    def __init__(self, x, y, char, color, name, hp, attack, defense, speed):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.speed = speed
        self.level = 1
        self.xp = 0
        self.stat_points = 0
        self.inventory = []

    def move(self, dx, dy, game_map):
        if not game_map.is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def take_damage(self, amount):
        self.hp -= amount
        return self.hp <= 0

    def gain_xp(self, amount):
        self.xp += amount
        threshold = self.level * 50
        if self.xp >= threshold:
            self.xp -= threshold
            self.level_up()

    def level_up(self):
        self.level += 1
        self.stat_points += 5
        print(f"{self.name} reached level {self.level}! Stat points +5")

    def attack_target(self, target):
        # Hit chance based on speed
        hit_chance = self.speed / (self.speed + target.speed)
        if random.random() < hit_chance:
            base_damage = random.randint(1, self.attack)
            damage = max(1, base_damage - target.defense)
        else:
            damage = 0
        died = target.take_damage(damage)
        if died:
            # XP reward if target has xp_yield
            xp_yield = getattr(target, 'xp_yield', 0)
            if xp_yield:
                self.gain_xp(xp_yield)
        return damage, died

# === Player Classes ===
class Warrior(Actor):
    def __init__(self, x, y):
        super().__init__(x, y, '@', (255, 255, 255), 'Warrior', hp=30, attack=5, defense=3, speed=2)

class Rogue(Actor):
    def __init__(self, x, y):
        super().__init__(x, y, '@', (0, 255, 0), 'Rogue', hp=20, attack=7, defense=2, speed=3)

class Mage(Actor):
    def __init__(self, x, y):
        super().__init__(x, y, '@', (0, 0, 255), 'Mage', hp=18, attack=9, defense=1, speed=2)

# === Monster Class ===
class Monster(Actor):
    def __init__(self, x, y, template):
        super().__init__(x, y, template['char'], template['color'], template['name'],
                         hp=template['hp'], attack=template['attack'],
                         defense=template['defense'], speed=template['speed'])
        self.xp_yield = template.get('xp', 0)

# === Monster Templates ===
monster_templates = [
    {'name': 'Rat', 'char': 'r', 'color': (150, 150, 150), 'hp': 10, 'attack': 3, 'defense': 0, 'speed': 2, 'xp': 10},
    {'name': 'Bat', 'char': 'b', 'color': (200, 200, 200), 'hp': 8, 'attack': 4, 'defense': 0, 'speed': 3, 'xp': 12},
    {'name': 'Goblin', 'char': 'g', 'color': (0, 150, 0), 'hp': 16, 'attack': 5, 'defense': 1, 'speed': 2, 'xp': 20},
    {'name': 'Skeleton', 'char': 's', 'color': (100, 100, 100), 'hp': 20, 'attack': 6, 'defense': 2, 'speed': 1, 'xp': 25},
    {'name': 'Ghost', 'char': 'G', 'color': (180, 180, 255), 'hp': 12, 'attack': 7, 'defense': 0, 'speed': 4, 'xp': 30},
]

# === Game Map ===
class GameMap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = self.initialize_tiles()
        self.rooms = []
        self.items = []
        self.create_rooms_and_corridors()
        self.place_items()

    def initialize_tiles(self):
        return [[Tile(True) for y in range(self.height)] for x in range(self.width)]

    def create_room(self, room):
        for x in range(room.x1 + 1, room.x2):
            for y in range(room.y1 + 1, room.y2):
                self.tiles[x][y].blocked = False
                self.tiles[x][y].block_sight = False

    def create_h_tunnel(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.tiles[x][y].blocked = False
            self.tiles[x][y].block_sight = False

    def create_v_tunnel(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.tiles[x][y].blocked = False
            self.tiles[x][y].block_sight = False

    def create_rooms_and_corridors(self):
        for _ in range(MAX_ROOMS):
            w = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
            h = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
            x = random.randint(0, self.width - w - 1)
            y = random.randint(0, self.height - h - 1)
            new_room = Rect(x, y, w, h)
            if any(new_room.intersect(other) for other in self.rooms):
                continue
            self.create_room(new_room)
            new_x, new_y = new_room.center()
            if self.rooms:
                prev_x, prev_y = self.rooms[-1].center()
                if random.choice([True, False]):
                    self.create_h_tunnel(prev_x, new_x, prev_y)
                    self.create_v_tunnel(prev_y, new_y, new_x)
                else:
                    self.create_v_tunnel(prev_y, new_y, prev_x)
                    self.create_h_tunnel(prev_x, new_x, new_y)
            self.rooms.append(new_room)

    def place_items(self):
        # Place a couple of health potions per room
        for room in self.rooms:
            num_items = random.randint(0, 2)
            for _ in range(num_items):
                x = random.randint(room.x1 + 1, room.x2 - 1)
                y = random.randint(room.y1 + 1, room.y2 - 1)
                potion = Item(x, y, 'Health Potion', '!', (255, 0, 0), effect='heal')
                self.items.append(potion)

    def is_blocked(self, x, y):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return True
        return self.tiles[x][y].blocked

# === Main Game ===
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Level World')
        self.clock = pygame.time.Clock()
        self.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT)
        self.actors = []

    def new_game(self, player_class):
        # Place player in first room center
        center_x, center_y = self.game_map.rooms[0].center()
        if player_class.lower() == 'warrior':
            self.player = Warrior(center_x, center_y)
        elif player_class.lower() == 'rogue':
            self.player = Rogue(center_x, center_y)
        elif player_class.lower() == 'mage':
            self.player = Mage(center_x, center_y)
        self.actors = [self.player]
        self.spawn_monsters()

    def spawn_monsters(self):
        for room in self.game_map.rooms[1:]:
            num_monsters = random.randint(0, 3)
            for _ in range(num_monsters):
                x = random.randint(room.x1 + 1, room.x2 - 1)
                y = random.randint(room.y1 + 1, room.y2 - 1)
                template = random.choice(monster_templates)
                monster = Monster(x, y, template)
                self.actors.append(monster)

    def handle_keys(self):
        moved = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'exit'
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.player.move(0, -1, self.game_map)
                    moved = True
                elif event.key == pygame.K_DOWN:
                    self.player.move(0, 1, self.game_map)
                    moved = True
                elif event.key == pygame.K_LEFT:
                    self.player.move(-1, 0, self.game_map)
                    moved = True
                elif event.key == pygame.K_RIGHT:
                    self.player.move(1, 0, self.game_map)
                    moved = True
        if moved:
            self.check_for_combat()
            self.check_for_items()
        return None

    def check_for_combat(self):
        # If player moves into a monster, resolve combat
        for actor in self.actors[:]:
            if actor is not self.player and actor.x == self.player.x and actor.y == self.player.y:
                damage, died = self.player.attack_target(actor)
                print(f"You hit {actor.name} for {damage} damage.")
                if died:
                    print(f"{actor.name} dies. You gain {actor.xp_yield} XP.")
                    self.actors.remove(actor)
                break

    def check_for_items(self):
        for item in self.game_map.items[:]:
            if item.x == self.player.x and item.y == self.player.y:
                self.player.inventory.append(item)
                self.game_map.items.remove(item)
                print(f"You picked up {item.name}.")
                break

    def render(self):
        self.screen.fill((0, 0, 0))
        # Camera viewport in tiles
        vp_w = SCREEN_WIDTH // TILE_SIZE
        vp_h = SCREEN_HEIGHT // TILE_SIZE
        cam_x = self.player.x - vp_w // 2
        cam_y = self.player.y - vp_h // 2
        cam_x = max(0, min(cam_x, self.game_map.width - vp_w))
        cam_y = max(0, min(cam_y, self.game_map.height - vp_h))

        # Draw map tiles
        for x in range(cam_x, cam_x + vp_w):
            for y in range(cam_y, cam_y + vp_h):
                tile = self.game_map.tiles[x][y]
                screen_x = (x - cam_x) * TILE_SIZE
                screen_y = (y - cam_y) * TILE_SIZE
                color = COLOR_DARK_WALL if tile.blocked else COLOR_DARK_FLOOR
                pygame.draw.rect(self.screen, color, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))

        # Draw items
        for item in self.game_map.items:
            if cam_x <= item.x < cam_x + vp_w and cam_y <= item.y < cam_y + vp_h:
                screen_x = (item.x - cam_x) * TILE_SIZE
                screen_y = (item.y - cam_y) * TILE_SIZE
                pygame.draw.rect(self.screen, item.color, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))

        # Draw actors
        for actor in self.actors:
            if cam_x <= actor.x < cam_x + vp_w and cam_y <= actor.y < cam_y + vp_h:
                screen_x = (actor.x - cam_x) * TILE_SIZE
                screen_y = (actor.y - cam_y) * TILE_SIZE
                pygame.draw.rect(self.screen, actor.color, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))

        pygame.display.flip()

    def run(self):
        while True:
            action = self.handle_keys()
            if action == 'exit':
                break
            self.render()
            self.clock.tick(30)
        pygame.quit()

if __name__ == '__main__':
    game = Game()
    game.new_game('warrior')
    game.run()
