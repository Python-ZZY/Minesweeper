try:
    import pyi_splash
    pyi_splash.close()
except:
    pass

from functools import lru_cache
from itertools import product
import asyncio
import pygame as pg
import random
import os
import sys

def path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.normpath(os.path.join(base_path, relative_path))

@lru_cache(1)
def load_font(size):
    return pg.font.Font(path("assets/font.ttf"), size)

@lru_cache()
def render(text, color=(255, 255, 255), size=16):
    return load_font(size).render(text, True, color)

@lru_cache()
def load_image(name, scale=None, flip=None):
    surf = pg.image.load(path("assets/"+name))
    if scale:
        surf = pg.transform.scale(surf, scale)
    if flip:
        surf = pg.transform.flip(surf, *flip)
        
    return surf

@lru_cache()
def load_sound(name):
    return pg.mixer.Sound(path("assets/" + name))

def play_sound(name):
    load_sound(name + ".ogg").play()
    
def generate_map(size, count):
    m = [[0 for _ in range(size)] for _ in range(size)]
    
    coord = list(product(range(size), range(size)))
    for x, y in random.sample(coord, count):
        m[x][y] = -1
        for x, y in product((x, x-1, x+1), (y, y-1, y+1)):
            try:
                if x == -1 or y == -1 or m[x][y] == -1:
                    continue
            except IndexError:
                continue
            m[x][y] += 1

    return m

class BlockOpener:
    def __init__(self, map):
        self.open_set = set()
        self.map = map
        self.d = len(map)

    def _open(self, x, y):
        m = self.map
        self.new_open_set.add((x, y))
        self.close_set.add((x, y))

        for x, y in product((x, x-1, x+1), (y, y-1, y+1)):
            if (x, y) not in self.close_set and 0 <= x < self.d and 0 <= y < self.d:
                if m[x][y] == 0:
                    self._open(x, y)
                else:
                    self.close_set.add((x, y))
                    if m[x][y] > 0:
                        self.new_open_set.add((x, y))

    def open(self, x, y):
        self.close_set = set()
        self.new_open_set = set()
        self.sound_state = "open"
        if not self.close_set and self.map[x][y] != 0:
            self.new_open_set.add((x, y))
            if self.map[x][y] == -1:
                self.sound_state = "lose"
            else:
                self.open_set.add((x, y))
            return
        self._open(x, y)
        self.open_set = self.open_set | self.new_open_set

pg.init()
for _, __, fs in os.walk(path("assets/")):
    for f in fs:
        if f.endswith("png"):
            load_image(f)
        elif f.endswith("ogg"):
            load_sound(f)

BLOCKCOLORS = (
        (0, 0, 255),
        (0, 255, 0),
        (255, 0, 0),
        (0, 180, 180),
        (255, 128, 0),
        (128, 0, 128),
        (0, 64, 64),
        (128, 64, 0)
        )
BG = (230, 230, 230)

screen = pg.display.set_mode((WIDTH := 300, HEIGHT := 330))
pg.display.set_caption("Mine Clearance")
pg.display.set_icon(load_image("icon.ico"))

clock = pg.time.Clock()

tip_surf = render("Total: 10 (Right click to mark)", (0, 0, 0))
tip_surf_rect = tip_surf.get_rect(center=(WIDTH/2, 20))

board = pg.Surface((288, 288))
board.fill((240, 240, 240))

BOARDSIZE = board.get_width()
board_rect = board.get_rect(centerx=WIDTH/2, bottom=HEIGHT-(WIDTH-BOARDSIZE)/2)

pause_surf = pg.Surface((BOARDSIZE, BOARDSIZE)).convert_alpha()
pause_surf.fill((255, 255, 255, 250))
r = render("- Pause -", color=(0, 0, 0), size=22)
pause_surf.blit(r, r.get_rect(center=(board_rect.width/2, board_rect.height/2)))

_res_mask = pg.Surface((WIDTH, HEIGHT)).convert_alpha()
_res_mask.fill((0, 0, 0, 100))
r = render("Press <Spacebar> to retry", size=16)
_res_mask.blit(r, r.get_rect(center=(WIDTH/2, 220)))

difficulty = 9
MINECOUNT = 10
BLOCKSIZE = BOARDSIZE / difficulty

_map_mask = pg.Surface((BOARDSIZE, BOARDSIZE)).convert_alpha()
_map_mask.fill((0, 0, 0, 0))
    
for y in range(difficulty):
    for x in range(difficulty):
        pos = (x * BLOCKSIZE, y * BLOCKSIZE)
        board.blit(load_image("block_down.png"), pos)
        _map_mask.blit(load_image("block.png"), pos)
        
async def main():
    while True:
        play_sound("new")
        
        map = generate_map(difficulty, MINECOUNT)
        block_opener = BlockOpener(map)
        pause = False
        map_mask = _map_mask.copy()
        res_mask = _res_mask.copy()
        marks = set()

        for y, line in enumerate(map):
            for x, block in enumerate(line):
                pos = (x * BLOCKSIZE, y * BLOCKSIZE)
                board.blit(load_image("block_down.png"), pos)
                map_mask.blit(load_image("block.png"), pos)
                
                if block == -1:
                    board.blit(load_image("mine.png"), pos)
                elif block > 0:
                    surf = render(str(block), BLOCKCOLORS[block-1])
                    rect = surf.get_rect(center=((x+0.5) * BLOCKSIZE, (y+0.5) * BLOCKSIZE))
                    board.blit(surf, rect)

        running = True
        while running:
            screen.fill(BG)
            screen.blit(tip_surf, tip_surf_rect)
            screen.blit(board, board_rect)
            screen.blit(map_mask, board_rect)
            for y, x in marks:
                screen.blit(load_image("mark.png"), (board_rect.x + x * BLOCKSIZE,
                                                     board_rect.y + y * BLOCKSIZE))
            if pause:
                screen.blit(pause_surf, board_rect)
                
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit()
                elif event.type == pg.MOUSEBUTTONDOWN:
                    if not pause and board_rect.collidepoint(event.pos):
                        y = (event.pos[0] - board_rect.x) // BLOCKSIZE
                        x = (event.pos[1] - board_rect.y) // BLOCKSIZE
                        if event.button == 1 and (x, y) not in marks:
                            block_opener.open(int(x), int(y))
                            for y, x in block_opener.new_open_set:
                                posx, posy = x * BLOCKSIZE, y * BLOCKSIZE
                                map_mask.set_clip((posx, posy, BLOCKSIZE, BLOCKSIZE))
                                map_mask.fill((0, 0, 0, 0))

                                if (y, x) in marks:
                                    marks.discard((y, x))

                            play_sound(state := block_opener.sound_state)
                            if state == "lose":
                                r = render("Game Over", size=26)
                                res_mask.blit(r, r.get_rect(center=(WIDTH/2, 120)))
                                running = False
                                break
                                
                        elif event.button == 3 and (x, y) not in block_opener.open_set:
                            if (x, y) in marks:
                                marks.discard((x, y))
                            else:
                                marks.add((x, y))
                            play_sound("mark")

                        if len(block_opener.open_set) + len(marks) == difficulty ** 2 and \
                           len(marks) == MINECOUNT:
                            r = render("You Win !", size=26)
                            res_mask.blit(r, r.get_rect(center=(WIDTH/2, 120)))
                            play_sound("win")
                            running = False
                            break
                        
                elif event.type == pg.KEYDOWN and event.key == pg.K_p:
                    pause = not pause
                    play_sound("do")

            clock.tick(60)
            pg.display.update()
            await asyncio.sleep(0)

        running = True       
        while running:
            screen.fill(BG)
            screen.blit(board, board_rect)
            screen.blit(res_mask, (0, 0))

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit()
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_SPACE:
                        running = False

            clock.tick(60)
            pg.display.update()
            await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())
