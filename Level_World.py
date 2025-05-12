"""
Level World: A turn-based roguelike using Pygame
Classes: Warrior, Rogue, Mage
Stats: HP, Attack, Defense, Speed
Map: Rectangular rooms + corridors
Monsters: Goblins, Skeletons, Rats, Bats, Ghosts
Inventory: infinite slots, loot drops, full combat exchange,
health/XP bars, openable inventory, stairs to next floor,
stats display, configurable window size & fullscreen
"""
import pygame
import random
import argparse

# === Default Game Settings ===
DEFAULT_SCREEN_WIDTH = 800
DEFAULT_SCREEN_HEIGHT = 600
TILE_SIZE = 32
MAP_WIDTH = 40
MAP_HEIGHT = 30
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 8
FONT_SIZE = 18

# === Colors ===
COLOR_DARK_WALL   = (0,   0,   100)
COLOR_DARK_FLOOR  = (50,  50,  150)
COLOR_HEALTH_BG   = (50,   0,   0)
COLOR_HEALTH_FG   = (200,  0,   0)
COLOR_XP_BG       = (0,   50,   0)
COLOR_XP_FG       = (0,   200,  0)
COLOR_TEXT        = (255, 255, 255)
COLOR_STAIRS      = (200, 200,  0)

# === Tile ===
class Tile:
    def __init__(self, blocked, block_sight=None):
        self.blocked = blocked
        self.block_sight = blocked if block_sight is None else block_sight
        self.explored = False

# === Item ===
class Item:
    def __init__(self, x, y, name, char, color, effect=None):
        self.x = x; self.y = y
        self.name = name; self.char = char; self.color = color; self.effect = effect

# === Rectangular Room ===
class Rect:
    def __init__(self, x, y, w, h):
        self.x1 = x; self.y1 = y
        self.x2 = x + w; self.y2 = y + h
    def center(self): return (self.x1 + self.x2)//2, (self.y1 + self.y2)//2
    def intersect(self, other):
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

# === Actor Base & Subclasses ===
class Actor:
    def __init__(self, x, y, char, color, name, hp, attack, defense, speed):
        self.x = x; self.y = y; self.char = char; self.color = color
        self.name = name; self.max_hp = hp; self.hp = hp
        self.attack = attack; self.defense = defense; self.speed = speed
        self.level = 1; self.xp = 0; self.stat_points = 0
        self.inventory = []
    def move(self, dx, dy, game_map):
        if not game_map.is_blocked(self.x+dx, self.y+dy): self.x += dx; self.y += dy
    def take_damage(self, amount): self.hp -= amount; return self.hp <= 0
    def gain_xp(self, amount):
        self.xp += amount; thresh = self.level * 50
        if self.xp >= thresh: self.xp -= thresh; self.level_up()
    def level_up(self): self.level += 1; self.stat_points += 5; print(f"{self.name} reached level {self.level}! +5 stat points")
    def attack_target(self, target):
        hit = self.speed / (self.speed + target.speed)
        if random.random() < hit: base = random.randint(1, self.attack); dmg = max(1, base - target.defense)
        else: dmg = 0
        died = target.take_damage(dmg)
        if died: self.gain_xp(getattr(target, 'xp_yield', 0))
        return dmg, died

class Warrior(Actor):
    def __init__(self, x, y): super().__init__(x, y, '@', (255,255,255), 'Warrior', 30, 5, 3, 2)
class Rogue(Actor):
    def __init__(self, x, y): super().__init__(x, y, '@', (0,255,0), 'Rogue', 20, 7, 2, 3)
class Mage(Actor):
    def __init__(self, x, y): super().__init__(x, y, '@', (0,0,255), 'Mage', 18, 9, 1, 2)

class Monster(Actor):
    def __init__(self, x, y, tmpl):
        super().__init__(x, y, tmpl['char'], tmpl['color'], tmpl['name'],
                         tmpl['hp'], tmpl['attack'], tmpl['defense'], tmpl['speed'])
        self.xp_yield = tmpl.get('xp', 0)

monster_templates = [
    {'name':'Rat','char':'r','color':(150,150,150),'hp':10,'attack':3,'defense':0,'speed':2,'xp':10},
    {'name':'Bat','char':'b','color':(200,200,200),'hp':8,'attack':4,'defense':0,'speed':3,'xp':12},
    {'name':'Goblin','char':'g','color':(0,150,0),'hp':16,'attack':5,'defense':1,'speed':2,'xp':20},
    {'name':'Skeleton','char':'s','color':(100,100,100),'hp':20,'attack':6,'defense':2,'speed':1,'xp':25},
    {'name':'Ghost','char':'G','color':(180,180,255),'hp':12,'attack':7,'defense':0,'speed':4,'xp':30},
]

# === Game Map ===
class GameMap:
    def __init__(self, width, height):
        self.width = width; self.height = height
        self.tiles = [[Tile(True) for _ in range(height)] for _ in range(width)]
        self.rooms = []; self.items = []
        self._create_rooms_and_corridors(); self._place_items()
        sx, sy = self.rooms[-1].center()
        stairs = Item(sx, sy, 'Stairs', '>', COLOR_STAIRS, effect='stairs')
        self.items.append(stairs); self.stairs = stairs
    def _create_rooms_and_corridors(self):
        for _ in range(MAX_ROOMS):
            w = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
            h = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
            x = random.randint(0, self.width-w-1); y = random.randint(0, self.height-h-1)
            r = Rect(x, y, w, h)
            if any(r.intersect(o) for o in self.rooms): continue
            # carve
            for ix in range(r.x1+1, r.x2):
                for iy in range(r.y1+1, r.y2): self.tiles[ix][iy].blocked=False; self.tiles[ix][iy].block_sight=False
            # tunnels
            if self.rooms:
                px, py = self.rooms[-1].center(); cx, cy = r.center()
                if random.choice([True,False]):
                    for ix in range(min(px,cx),max(px,cx)+1): self.tiles[ix][py].blocked=False; self.tiles[ix][py].block_sight=False
                    for iy in range(min(py,cy),max(py,cy)+1): self.tiles[cx][iy].blocked=False; self.tiles[cx][iy].block_sight=False
                else:
                    for iy in range(min(py,cy),max(py,cy)+1): self.tiles[px][iy].blocked=False; self.tiles[px][iy].block_sight=False
                    for ix in range(min(px,cx),max(px,cx)+1): self.tiles[ix][cy].blocked=False; self.tiles[ix][cy].block_sight=False
            self.rooms.append(r)
    def _place_items(self):
        for room in self.rooms:
            for _ in range(random.randint(0,2)):
                ix = random.randint(room.x1+1, room.x2-1); iy = random.randint(room.y1+1, room.y2-1)
                self.items.append(Item(ix, iy, 'Health Potion', '!', (255,0,0), effect='heal'))
    def is_blocked(self, x, y):
        if x<0 or x>=self.width or y<0 or y>=self.height: return True
        return self.tiles[x][y].blocked

# === Main Game ===
class Game:
    def __init__(self, screen_width, screen_height, fullscreen=False):
        pygame.init(); pygame.font.init()
        flags = pygame.FULLSCREEN if fullscreen else 0
        self.screen = pygame.display.set_mode((screen_width, screen_height), flags)
        pygame.display.set_caption('Level World')
        self.font = pygame.font.SysFont(None, FONT_SIZE)
        self.clock = pygame.time.Clock()
        self.screen_width = screen_width; self.screen_height = screen_height
        self.show_inventory = False
        self.next_floor()

    def next_floor(self):
        # regenerate map, keep player state
        if hasattr(self, 'player'):
            inv, lvl, xp = self.player.inventory, self.player.level, self.player.xp
        else:
            inv, lvl, xp = [], 1, 0
        self.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT)
        cx, cy = self.game_map.rooms[0].center()
        if not hasattr(self, 'player'):
            self.player = Warrior(cx, cy)
        self.player.x, self.player.y = cx, cy
        self.player.inventory, self.player.level, self.player.xp = inv, lvl, xp
        self.actors = [self.player]; self._spawn_monsters()

    def _spawn_monsters(self):
        for room in self.game_map.rooms[1:]:
            for _ in range(random.randint(0,3)):
                mx = random.randint(room.x1+1, room.x2-1); my = random.randint(room.y1+1, room.y2-1)
                self.actors.append(Monster(mx, my, random.choice(monster_templates)))

    def handle_keys(self):
        moved = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return 'exit'
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_i: self.show_inventory = not self.show_inventory
                if e.key == pygame.K_ESCAPE: return 'exit'
                dirs = {pygame.K_UP:(0,-1),pygame.K_DOWN:(0,1),pygame.K_LEFT:(-1,0),pygame.K_RIGHT:(1,0)}
                if e.key in dirs and not self.show_inventory:
                    dx, dy = dirs[e.key]; self.player.move(dx, dy, self.game_map); moved = True
        if moved:
            self._combat_and_items()
        return None

    def _combat_and_items(self):
        # combat
        for a in self.actors[:]:
            if a is not self.player and a.x==self.player.x and a.y==self.player.y:
                dmg,died = self.player.attack_target(a)
                print(f"You hit {a.name} for {dmg}.")
                if died:
                    print(f"{a.name} dies. +{a.xp_yield} XP")
                    self.actors.remove(a)
                else:
                    md, _ = a.attack_target(self.player)
                    print(f"{a.name} hits you for {md}.")
                break
        # items & stairs
        for it in self.game_map.items[:]:
            if it.x==self.player.x and it.y==self.player.y:
                if it.effect=='heal': self.player.hp=min(self.player.max_hp,self.player.hp+10); print("Healed.")
                elif it.effect=='stairs': print("Descending..."); self.next_floor(); return
                self.player.inventory.append(it); self.game_map.items.remove(it); print(f"Picked up {it.name}.")
                break

    def render_bars(self):
        x, y = 10, 10; w, h = 200, 20
        # HP
        pygame.draw.rect(self.screen, COLOR_HEALTH_BG, (x, y, w, h))
        pygame.draw.rect(self.screen, COLOR_HEALTH_FG, (x, y, int(w*self.player.hp/self.player.max_hp), h))
        self.screen.blit(self.font.render(f"HP {self.player.hp}/{self.player.max_hp}",True,COLOR_TEXT),(x+5,y+2))
        # XP
        y += h+5
        pygame.draw.rect(self.screen, COLOR_XP_BG, (x, y, w, h))
        pygame.draw.rect(self.screen, COLOR_XP_FG, (x, y, int(w*self.player.xp/(self.player.level*50)), h))
        self.screen.blit(self.font.render(f"XP {self.player.xp}/{self.player.level*50}",True,COLOR_TEXT),(x+5,y+2))
        # Stats
        y += h+5
        stats = f"Lvl {self.player.level}  Atk {self.player.attack}  Def {self.player.defense}  Spd {self.player.speed}"
        self.screen.blit(self.font.render(stats,True,COLOR_TEXT),(x, y))

    def render(self):
        self.screen.fill((0,0,0))
        vp_w = self.screen_width//TILE_SIZE; vp_h = self.screen_height//TILE_SIZE
        cx = max(0, min(self.player.x-vp_w//2, self.game_map.width-vp_w))
        cy = max(0, min(self.player.y-vp_h//2, self.game_map.height-vp_h))
        # draw map
        for ix in range(cx, cx+vp_w):
            for iy in range(cy, cy+vp_h):
                t = self.game_map.tiles[ix][iy]
                c = COLOR_DARK_WALL if t.blocked else COLOR_DARK_FLOOR
                pygame.draw.rect(self.screen, c, ((ix-cx)*TILE_SIZE, (iy-cy)*TILE_SIZE, TILE_SIZE, TILE_SIZE))
        # stairs
        sx, sy = self.game_map.stairs.x, self.game_map.stairs.y
        if cx<=sx<cx+vp_w and cy<=sy<cy+vp_h:
            pygame.draw.rect(self.screen, COLOR_STAIRS, ((sx-cx)*TILE_SIZE,(sy-cy)*TILE_SIZE,TILE_SIZE,TILE_SIZE))
        # items
        for it in self.game_map.items:
            if cx<=it.x<cx+vp_w and cy<=it.y<cy+vp_h:
                pygame.draw.rect(self.screen, it.color, ((it.x-cx)*TILE_SIZE,(it.y-cy)*TILE_SIZE,TILE_SIZE,TILE_SIZE))
        # actors
        for a in self.actors:
            if cx<=a.x<cx+vp_w and cy<=a.y<cy+vp_h:
                pygame.draw.rect(self.screen,a.color,((a.x-cx)*TILE_SIZE,(a.y-cy)*TILE_SIZE,TILE_SIZE,TILE_SIZE))
        # UI
        self.render_bars()
        if self.show_inventory:
            lines = [f"Inventory ({len(self.player.inventory)})"] + [f"- {i.name}" for i in self.player.inventory]
            for i,line in enumerate(lines):
                self.screen.blit(self.font.render(line,True,COLOR_TEXT),(10,self.screen_height-(len(lines)-i)*FONT_SIZE-10))
        pygame.display.flip()

    def run(self):
        while True:
            if self.handle_keys()=='exit': break
            self.render(); self.clock.tick(30)
        pygame.quit()

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Level World Roguelike')
    parser.add_argument('--width', type=int, default=DEFAULT_SCREEN_WIDTH, help='Window width')
    parser.add_argument('--height', type=int, default=DEFAULT_SCREEN_HEIGHT, help='Window height')
    parser.add_argument('--fullscreen', action='store_true', help='Start in fullscreen')
    args = parser.parse_args()
    game = Game(args.width, args.height, args.fullscreen)
    game.run()
