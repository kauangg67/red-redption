#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRONTEIRA SELVAGEM - um faroeste de mundo aberto (visao de cima) feito em Pygame.

Controles
---------
WASD / Setas ... andar (cavalo: conduzir)
SHIFT .......... correr / galopar
Mouse .......... mirar        Clique esquerdo ... atirar
R .............. recarregar   (ou renascer, quando morto)
ESPACO ......... Olho Mortal (camera lenta + mira automatica perto do cursor)
E .............. montar / desmontar do cavalo
Q .............. tomar tonico (cura)
P .............. pausar       ESC ... sair

Instalar:  pip install pygame      Rodar:  python fronteira_selvagem.py
"""
import math
import random
import sys

import pygame
from pygame.math import Vector2 as V

# ----------------------------------------------------------------------------
# Constantes
# ----------------------------------------------------------------------------
W, H = 1280, 720
FPS = 60
WORLD_W, WORLD_H = 4200, 3200
ROAD_Y = 1600
TOWN = pygame.Rect(1500, 1250, 1200, 700)
DAY_SECONDS = 240.0          # duracao de um dia inteiro em segundos reais
MM_W, MM_H = 190, 144        # minimapa


def clamp(v, a, b):
    return max(a, min(b, v))


def angle_lerp(a, b, t):
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    return a + d * min(1.0, t)


def shade(c, k):
    return tuple(clamp(int(x + k), 0, 255) for x in c)


def make_font(size, bold=False):
    return pygame.font.SysFont("georgia,palatino,timesnewroman,serif", size, bold=bold)


def move_with_collision(pos, delta, radius, obstacles):
    """Move 'pos' (Vector2) por 'delta' colidindo com retangulos."""
    pos.x += delta.x
    r = pygame.Rect(0, 0, int(radius * 2), int(radius * 2))
    r.center = (int(pos.x), int(pos.y))
    for o in obstacles:
        if r.colliderect(o):
            if delta.x > 0:
                pos.x = o.left - radius
            elif delta.x < 0:
                pos.x = o.right + radius
            r.centerx = int(pos.x)
    pos.y += delta.y
    r.center = (int(pos.x), int(pos.y))
    for o in obstacles:
        if r.colliderect(o):
            if delta.y > 0:
                pos.y = o.top - radius
            elif delta.y < 0:
                pos.y = o.bottom + radius
            r.centery = int(pos.y)
    pos.x = clamp(pos.x, radius, WORLD_W - radius)
    pos.y = clamp(pos.y, radius, WORLD_H - radius)


def road_y(x):
    fade = clamp((abs(x - 2100) - 650) / 500.0, 0, 1)
    return ROAD_Y + 240 * math.sin(x / 640.0) * fade


def road_x(y):
    fade = clamp((abs(y - 1600) - 450) / 500.0, 0, 1)
    return 2100 + 200 * math.sin(y / 520.0) * fade


# ----------------------------------------------------------------------------
# Mundo (gerado proceduralmente e "assado" em uma imagem grande)
# ----------------------------------------------------------------------------
class World:
    def __init__(self, font):
        rng = random.Random(1899)
        self.obstacles = []
        self.camps = [V(520, 520), V(3650, 560), V(680, 2650), V(3500, 2700),
                      V(2050, 480), V(2150, 2850), V(420, 1550), V(3800, 1650)]
        self.bg = pygame.Surface((WORLD_W, WORLD_H))
        self._terrain(rng)
        self._roads()
        self._pebbles(rng)
        self._props(rng)
        self._town(font)
        self._camps(rng)
        self.mini = pygame.transform.smoothscale(self.bg, (MM_W, MM_H))

    # -- terreno -------------------------------------------------------------
    def _terrain(self, rng):
        bg = self.bg
        bg.fill((196, 166, 112))
        for _ in range(900):
            x, y = rng.randrange(WORLD_W), rng.randrange(WORLD_H)
            r = rng.randrange(40, 130)
            k = rng.randint(-12, 12)
            if rng.random() < 0.28:
                col = (148 + k, 150 + k, 88 + k)       # capim seco
            else:
                col = (196 + k, 166 + k, 112 + k)      # areia
            pygame.draw.circle(bg, col, (x, y), r)

    def _roads(self):
        pts_h = [(x, road_y(x)) for x in range(-40, WORLD_W + 60, 24)]
        pts_v = [(road_x(y), y) for y in range(-40, WORLD_H + 60, 24)]
        for pts in (pts_h, pts_v):
            for p in pts:
                pygame.draw.circle(self.bg, (166, 134, 92), p, 56)
        for pts in (pts_h, pts_v):
            for p in pts:
                pygame.draw.circle(self.bg, (181, 150, 105), p, 46)

    def _pebbles(self, rng):
        for _ in range(5000):
            x, y = rng.randrange(WORLD_W), rng.randrange(WORLD_H)
            c = self.bg.get_at((x, y))[:3]
            pygame.draw.circle(self.bg, shade(c, -22), (x, y), rng.randint(1, 3))

    # -- rochas, cactos, arbustos ---------------------------------------------
    def _props(self, rng):
        bg = self.bg
        zone = TOWN.inflate(260, 260)
        for _ in range(75):
            c = V(rng.randrange(100, WORLD_W - 100), rng.randrange(100, WORLD_H - 100))
            if zone.collidepoint(c.x, c.y):
                continue
            if any((c - camp).length() < 260 for camp in self.camps):
                continue
            r = rng.randint(22, 52)
            n = 9
            pts = []
            for i in range(n):
                a = i / n * math.tau
                rr = r * rng.uniform(0.75, 1.1)
                pts.append((c.x + math.cos(a) * rr, c.y + math.sin(a) * rr))
            base = rng.randint(-12, 12)
            col = (122 + base, 116 + base, 108 + base)
            pygame.draw.polygon(bg, (120, 92, 60), [(x + 7, y + 7) for x, y in pts])
            pygame.draw.polygon(bg, col, pts)
            pygame.draw.polygon(bg, shade(col, 22), [(c.x + (x - c.x) * 0.6 - 3, c.y + (y - c.y) * 0.6 - 3) for x, y in pts])
            pygame.draw.polygon(bg, shade(col, -45), pts, 2)
            self.obstacles.append(pygame.Rect(int(c.x - r * 0.75), int(c.y - r * 0.75), int(r * 1.5), int(r * 1.5)))
        for _ in range(170):
            c = V(rng.randrange(60, WORLD_W - 60), rng.randrange(60, WORLD_H - 60))
            if zone.collidepoint(c.x, c.y):
                continue
            if rng.random() < 0.55:   # cacto
                pygame.draw.circle(bg, (110, 90, 60), (c.x + 4, c.y + 5), 9)
                pygame.draw.circle(bg, (62, 118, 66), c, 8)
                pygame.draw.circle(bg, (88, 150, 90), (c.x - 2, c.y - 2), 4)
                for a in (rng.uniform(0, 6.28), rng.uniform(0, 6.28)):
                    pygame.draw.circle(bg, (62, 118, 66), (c.x + math.cos(a) * 11, c.y + math.sin(a) * 11), 5)
            else:                     # arbusto seco
                for _ in range(5):
                    o = V(rng.uniform(-9, 9), rng.uniform(-9, 9))
                    pygame.draw.circle(bg, (112, 104, 58), c + o, rng.randint(5, 9))
                pygame.draw.circle(bg, (136, 128, 72), c, 5)

    # -- cidade -----------------------------------------------------------------
    def _building(self, rect, name, wall, roof, font, door_down):
        bg = self.bg
        pygame.draw.rect(bg, (122, 94, 60), rect.move(10, 10))
        pygame.draw.rect(bg, wall, rect)
        roof_r = rect.inflate(-10, -10)
        pygame.draw.rect(bg, roof, roof_r)
        for x in range(roof_r.left, roof_r.right, 14):
            pygame.draw.line(bg, shade(roof, -26), (x, roof_r.top), (x, roof_r.bottom), 2)
        pygame.draw.rect(bg, (40, 25, 12), rect, 3)
        txt = font.render(name, True, (245, 230, 190))
        pad = pygame.Rect(0, 0, txt.get_width() + 16, txt.get_height() + 8)
        pad.center = roof_r.center
        pygame.draw.rect(bg, (60, 38, 20), pad, border_radius=4)
        bg.blit(txt, txt.get_rect(center=pad.center))
        dy = rect.bottom - 6 if door_down else rect.top - 4
        pygame.draw.rect(bg, (30, 18, 10), (rect.centerx - 14, dy, 28, 10))
        self.obstacles.append(rect.copy())

    def _town(self, font):
        top = [(1580, 1370, 220, 140, "SALOON", (120, 76, 44), (150, 60, 40)),
               (1850, 1390, 160, 120, "XERIFE", (110, 90, 60), (90, 80, 70)),
               (2200, 1370, 200, 140, "BANCO", (130, 112, 84), (70, 90, 70)),
               (2450, 1390, 180, 120, "EMPORIO", (118, 80, 50), (160, 110, 60))]
        bottom = [(1620, 1690, 200, 130, "HOTEL", (126, 92, 62), (110, 70, 60)),
                  (1870, 1690, 160, 130, "ESTABULO", (104, 76, 48), (130, 100, 60)),
                  (2220, 1690, 190, 130, "BARBEIRO", (130, 98, 70), (80, 100, 120)),
                  (2460, 1690, 160, 130, "IGREJA", (200, 190, 170), (150, 70, 60))]
        for x, y, w, h, name, wall, roof in top:
            self._building(pygame.Rect(x, y, w, h), name, wall, roof, font, True)
        for x, y, w, h, name, wall, roof in bottom:
            self._building(pygame.Rect(x, y, w, h), name, wall, roof, font, False)
        for bx, by in [(1830, 1530), (2430, 1530), (1845, 1670), (2435, 1670), (2060, 1530), (2140, 1670)]:
            pygame.draw.circle(self.bg, (100, 76, 52), (bx + 3, by + 4), 13)
            pygame.draw.circle(self.bg, (116, 74, 38), (bx, by), 12)
            pygame.draw.circle(self.bg, (80, 50, 24), (bx, by), 12, 2)
            pygame.draw.circle(self.bg, (146, 100, 56), (bx, by), 6)
            self.obstacles.append(pygame.Rect(bx - 11, by - 11, 22, 22))

    # -- acampamentos de bandidos --------------------------------------------------
    def _camps(self, rng):
        bg = self.bg
        for c in self.camps:
            pygame.draw.circle(bg, (120, 100, 76), c, 70)
            pygame.draw.circle(bg, (96, 80, 60), c, 22)
            for i in range(10):
                a = i / 10 * math.tau
                pygame.draw.circle(bg, (112, 110, 106), (c.x + math.cos(a) * 20, c.y + math.sin(a) * 20), 5)
            pygame.draw.line(bg, (70, 44, 22), c + V(-12, 6), c + V(12, -6), 5)
            pygame.draw.line(bg, (80, 50, 26), c + V(-10, -8), c + V(10, 9), 5)
            for off, col in ((V(-110, -50), (214, 198, 162)), (V(95, -70), (150, 122, 92))):
                t = pygame.Rect(0, 0, 70, 50)
                t.center = (int(c.x + off.x), int(c.y + off.y))
                pygame.draw.rect(bg, (110, 88, 60), t.move(7, 7))
                pygame.draw.rect(bg, col, t)
                pygame.draw.line(bg, shade(col, -50), (t.left, t.centery), (t.right, t.centery), 3)
                pygame.draw.rect(bg, shade(col, -70), t, 2)
                self.obstacles.append(t)
            for off in (V(60, 55), V(-70, 60)):
                cr = pygame.Rect(0, 0, 26, 26)
                cr.center = (int(c.x + off.x), int(c.y + off.y))
                pygame.draw.rect(bg, (140, 100, 56), cr)
                pygame.draw.rect(bg, (80, 54, 28), cr, 2)
                pygame.draw.line(bg, (80, 54, 28), cr.topleft, cr.bottomright, 2)
                self.obstacles.append(cr)

    def hit_obstacle(self, p):
        for o in self.obstacles:
            if o.collidepoint(p):
                return True
        return False

    def blocked(self, pos, r):
        rect = pygame.Rect(int(pos.x - r), int(pos.y - r), int(r * 2), int(r * 2))
        return rect.collidelist(self.obstacles) != -1


# ----------------------------------------------------------------------------
# Sprites desenhados por codigo
# ----------------------------------------------------------------------------
def make_horse_sprite():
    s = pygame.Surface((96, 44), pygame.SRCALPHA)
    body, dark = (122, 74, 36), (66, 38, 20)
    for (x, y) in [(22, 3), (22, 35), (54, 3), (54, 35)]:
        pygame.draw.ellipse(s, dark, (x, y, 14, 7))
    pygame.draw.ellipse(s, body, (14, 8, 58, 28))
    pygame.draw.ellipse(s, body, (62, 13, 28, 18))
    pygame.draw.ellipse(s, dark, (80, 16, 14, 12))
    pygame.draw.polygon(s, dark, [(66, 14), (70, 6), (75, 14)])
    pygame.draw.polygon(s, dark, [(66, 30), (70, 38), (75, 30)])
    pygame.draw.polygon(s, dark, [(16, 20), (2, 13), (0, 24), (2, 33), (16, 26)])
    pygame.draw.line(s, dark, (60, 18), (64, 22), 3)
    pygame.draw.rect(s, (150, 40, 30), (34, 13, 18, 18), border_radius=4)
    pygame.draw.rect(s, (60, 20, 15), (34, 13, 18, 18), 2, border_radius=4)
    return s


def make_deer_sprite():
    s = pygame.Surface((54, 30), pygame.SRCALPHA)
    body, dark = (176, 124, 72), (110, 74, 40)
    pygame.draw.ellipse(s, body, (6, 8, 34, 14))
    pygame.draw.ellipse(s, body, (34, 10, 14, 10))
    pygame.draw.line(s, dark, (40, 10), (44, 3), 2)
    pygame.draw.line(s, dark, (44, 3), (49, 4), 2)
    pygame.draw.line(s, dark, (40, 20), (44, 27), 2)
    pygame.draw.line(s, dark, (44, 27), (49, 26), 2)
    pygame.draw.circle(s, (240, 236, 224), (6, 15), 3)
    return s


LOOKS = [
    {"brim": (50, 50, 52), "crown": (72, 72, 76), "shirt": (140, 40, 36), "band": (200, 60, 50)},
    {"brim": (88, 66, 40), "crown": (112, 86, 52), "shirt": (70, 80, 60), "band": (230, 220, 190)},
    {"brim": (34, 28, 24), "crown": (56, 46, 40), "shirt": (60, 60, 90), "band": (180, 140, 40)},
]


# ----------------------------------------------------------------------------
# Entidades
# ----------------------------------------------------------------------------
class Bullet:
    __slots__ = ("pos", "vel", "owner", "dmg", "life")

    def __init__(self, pos, vel, owner, dmg, life=1.0):
        self.pos, self.vel, self.owner, self.dmg, self.life = V(pos), V(vel), owner, dmg, life


class Particle:
    __slots__ = ("pos", "vel", "life", "max", "col", "size")

    def __init__(self, pos, vel, life, col, size):
        self.pos, self.vel, self.life, self.max, self.col, self.size = V(pos), V(vel), life, life, col, size


class Pickup:
    def __init__(self, pos, kind, val):
        self.pos, self.kind, self.val, self.life = V(pos), kind, val, 70.0


class Horse:
    def __init__(self, pos):
        self.pos = V(pos)
        self.vel = V()
        self.angle = 0.0

    def update_mounted(self, move, dt, world, sprint):
        top = 430 if sprint else 290
        target = move * top
        self.vel += (target - self.vel) * min(1.0, 2.6 * dt)
        if self.vel.length() > 6:
            self.angle = angle_lerp(self.angle, math.atan2(self.vel.y, self.vel.x), 7 * dt)
            before = V(self.pos)
            move_with_collision(self.pos, self.vel * dt, 20, world.obstacles)
            if (self.pos - before).length() < self.vel.length() * dt * 0.4:
                self.vel *= 0.5


class Deer:
    def __init__(self, pos):
        self.pos = V(pos)
        self.hp = 18
        self.angle = random.uniform(0, math.tau)
        self.vel = V()
        self.wt = 0.0
        self.flee = 0.0

    def update(self, dt, g):
        to = self.pos - g.player_pos
        d = to.length()
        self.flee -= dt
        if (d < 260 and g.hp > 0) or self.flee > 0:
            if d > 1:
                self.vel = (to / d) * 240
            if d < 260:
                self.flee = 1.0
        else:
            self.wt -= dt
            if self.wt <= 0:
                self.wt = random.uniform(2, 5)
                self.vel = V() if random.random() < 0.45 else V(1, 0).rotate(random.uniform(0, 360)) * 32
        if self.vel.length_squared() > 1:
            self.angle = angle_lerp(self.angle, math.atan2(self.vel.y, self.vel.x), 10 * dt)
            move_with_collision(self.pos, self.vel * dt, 12, g.world.obstacles)


class Outlaw:
    def __init__(self, pos, hunting=False):
        self.pos = V(pos)
        self.home = V(pos)
        self.hp = 45
        self.angle = random.uniform(0, math.tau)
        self.cool = random.uniform(1.0, 2.5)
        self.hunting = hunting
        self.alert = hunting
        self.wdir = V()
        self.wt = 0.0
        self.look = random.choice(LOOKS)
        self.strafe = random.choice((-1, 1))
        self.st = 0.0
        self.flash = 0.0
        self.hurt = 0.0

    def update(self, dt, g):
        to = g.player_pos - self.pos
        d = to.length()
        alive = g.hp > 0
        if alive and d < 480:
            self.alert = True
        elif d > 760 and not self.hunting:
            self.alert = False
        if self.hunting and alive and d < 950:
            self.alert = True
        vel = V()
        if self.alert and alive:
            dirn = to / d if d > 1 else V(1, 0)
            self.angle = angle_lerp(self.angle, math.atan2(to.y, to.x), 9 * dt)
            perp = V(-dirn.y, dirn.x) * self.strafe
            if d > 300:
                vel = dirn * 95 + perp * 30
            elif d < 170:
                vel = -dirn * 85 + perp * 40
            else:
                vel = perp * 60
            self.st -= dt
            if self.st <= 0:
                self.st = random.uniform(1, 3)
                self.strafe = random.choice((-1, 1))
            self.cool -= dt
            if self.cool <= 0 and d < 520:
                self.cool = random.uniform(1.1, 2.3)
                a = math.atan2(to.y, to.x) + random.gauss(0, 0.05 + d / 6000.0)
                direction = V(math.cos(a), math.sin(a))
                g.bullets.append(Bullet(self.pos + direction * 24, direction * 700, "e", 9, 1.0))
                self.flash = 0.08
                g.burst(self.pos + direction * 26, (255, 220, 120), 4, 140)
        else:
            self.wt -= dt
            if self.wt <= 0:
                self.wt = random.uniform(2, 5)
                if not self.hunting and (self.pos - self.home).length() > 150:
                    self.wdir = (self.home - self.pos).normalize() * 35
                elif random.random() < 0.4:
                    self.wdir = V()
                else:
                    self.wdir = V(1, 0).rotate(random.uniform(0, 360)) * 35
            vel = self.wdir
            if vel.length_squared() > 1:
                self.angle = angle_lerp(self.angle, math.atan2(vel.y, vel.x), 6 * dt)
        if vel.length_squared() > 1:
            move_with_collision(self.pos, vel * dt, 13, g.world.obstacles)
        self.flash -= dt
        self.hurt -= dt


# ----------------------------------------------------------------------------
# Jogo
# ----------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Fronteira Selvagem - um faroeste em Pygame")
        self.clock = pygame.time.Clock()
        self.f_s = make_font(17)
        self.f_m = make_font(24, True)
        self.f_l = make_font(56, True)
        self.f_xl = make_font(92, True)
        self.f_tiny = make_font(13, True)
        self.world = World(self.f_tiny)
        self.horse_img = make_horse_sprite()
        self.deer_img = make_deer_sprite()
        self.night = pygame.Surface((W, H))
        self.warm = pygame.Surface((W, H))
        self.sepia = pygame.Surface((W, H))
        self.sepia.fill((190, 135, 50))
        self.sepia.set_alpha(60)
        self.vignette = self._make_vignette()
        self.menu_bg = self._make_menu_bg()
        self.state = "menu"
        self.paused = False
        self.cam = V()
        self.view = V()
        pygame.mouse.set_visible(False)
        self.reset()

    # -- preparos --------------------------------------------------------------
    def _make_vignette(self):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(60):
            a = int(150 * (1 - i / 60.0) ** 2)
            pygame.draw.rect(v, (0, 0, 0, a), (i * 5, int(i * 3.4), W - i * 10, H - int(i * 6.8)), 6)
        return v

    def _make_menu_bg(self):
        s = pygame.Surface((W, H))
        for y in range(H):
            t = y / H
            c = (int(240 - 170 * t), int(150 - 110 * t), int(70 - 30 * t))
            pygame.draw.line(s, c, (0, y), (W, y))
        pygame.draw.circle(s, (255, 214, 130), (W // 2, int(H * 0.58)), 150)
        pygame.draw.circle(s, (255, 236, 180), (W // 2, int(H * 0.58)), 110)
        pygame.draw.polygon(s, (60, 30, 28), [(0, H), (0, 520), (140, 470), (230, 470), (330, 540), (470, 500), (600, 560), (760, 520), (900, 470), (1010, 470), (1100, 530), (1280, 490), (W, H)])
        pygame.draw.polygon(s, (30, 14, 16), [(0, H), (0, 640), (260, 610), (520, 650), (820, 620), (1100, 660), (W, 630), (W, H)])
        return s

    def reset(self):
        self.player_pos = V(2100, 1640)
        self.player_angle = 0.0
        self.hp = 100.0
        self.max_hp = 100.0
        self.ammo = 6
        self.reserve = 36
        self.tonics = 3
        self.dead_eye = 35.0
        self.dead_eye_on = False
        self.money = 50
        self.mounted = False
        self.horse = Horse(V(2030, 1660))
        self.bullets, self.enemies, self.animals = [], [], []
        self.pickups, self.particles, self.msgs = [], [], []
        self.shoot_cd = 0.0
        self.reload_t = 0.0
        self.hurt_t = 0.0
        self.since_hit = 99.0
        self.flash = 0.0
        self.shake = 0.0
        self.kills = 0
        self.mission_level = 1
        self.mission_goal = 6
        self.mission_n = 0
        self.time = 8.0
        self.spawn_t = 8.0
        self.dust_t = 0.0
        for camp in self.world.camps:
            for _ in range(random.randint(2, 3)):
                p = self.free_pos(camp, 60)
                self.enemies.append(Outlaw(p))
        for _ in range(14):
            self.animals.append(Deer(self.random_free()))
        self.cam = self.player_pos - V(W / 2, H / 2)
        self.view = V(self.cam)
        self.say("Bem-vindo a fronteira, forasteiro. Cuidado com os bandidos.")

    # -- utilidades ---------------------------------------------------------------
    def say(self, text):
        self.msgs.append([text, 4.0])
        self.msgs = self.msgs[-5:]

    def free_pos(self, center, spread):
        for _ in range(40):
            p = V(center) + V(random.uniform(-spread, spread), random.uniform(-spread, spread))
            p.x = clamp(p.x, 40, WORLD_W - 40)
            p.y = clamp(p.y, 40, WORLD_H - 40)
            if not self.world.blocked(p, 16):
                return p
        return V(center)

    def random_free(self):
        for _ in range(60):
            p = V(random.randrange(100, WORLD_W - 100), random.randrange(100, WORLD_H - 100))
            if TOWN.inflate(200, 200).collidepoint(p.x, p.y):
                continue
            if not self.world.blocked(p, 16):
                return p
        return V(300, 300)

    def burst(self, pos, col, n, speed):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(0.3, 1.0) * speed
            self.particles.append(Particle(pos, V(math.cos(a), math.sin(a)) * sp, random.uniform(0.25, 0.6), col, random.uniform(2, 4)))

    def aim_world(self):
        return V(pygame.mouse.get_pos()) + self.view

    # -- acoes do jogador ---------------------------------------------------------------
    def shoot(self):
        if self.hp <= 0 or self.paused or self.state != "play":
            return
        if self.reload_t > 0 or self.shoot_cd > 0:
            return
        if self.ammo <= 0:
            self.start_reload()
            return
        aim = self.aim_world()
        ang = math.atan2(aim.y - self.player_pos.y, aim.x - self.player_pos.x)
        dmg = 26
        spread = 0.015 if not self.mounted else 0.07
        if self.dead_eye_on:
            best, bd = None, 230.0
            for t in self.enemies + self.animals:
                d = (t.pos - aim).length()
                if d < bd:
                    best, bd = t, d
            if best is not None:
                ang = math.atan2(best.pos.y - self.player_pos.y, best.pos.x - self.player_pos.x)
                spread = 0.0
                dmg = 48
        ang += random.gauss(0, spread)
        d = V(math.cos(ang), math.sin(ang))
        self.bullets.append(Bullet(self.player_pos + d * 28, d * 1300, "p", dmg, 0.9))
        self.ammo -= 1
        self.shoot_cd = 0.26
        self.flash = 0.07
        self.shake = min(8, self.shake + 3)
        self.burst(self.player_pos + d * 30, (255, 225, 130), 5, 180)

    def start_reload(self):
        if self.reload_t <= 0 and self.ammo < 6 and self.reserve > 0 and self.hp > 0:
            self.reload_t = 1.5

    def use_tonic(self):
        if self.hp > 0 and self.tonics > 0 and self.hp < self.max_hp:
            self.tonics -= 1
            self.hp = min(self.max_hp, self.hp + 45)
            self.say("Voce tomou um tonico (+45 de saude).")

    def toggle_mount(self):
        if self.hp <= 0:
            return
        if self.mounted:
            self.mounted = False
            self.horse.vel = V()
            side = V(-math.sin(self.horse.angle), math.cos(self.horse.angle)) * 36
            p = self.horse.pos + side
            self.player_pos = p if not self.world.blocked(p, 13) else V(self.horse.pos)
        elif (self.horse.pos - self.player_pos).length() < 90:
            self.mounted = True
            self.player_pos = V(self.horse.pos)

    def respawn(self):
        self.money = int(self.money * 0.8)
        self.hp = self.max_hp
        self.player_pos = V(2100, 1640)
        self.mounted = False
        self.horse.pos = V(2030, 1660)
        self.horse.vel = V()
        self.bullets.clear()
        self.reload_t = 0
        self.since_hit = 99
        self.say("Voce acordou na cidade. Perdeu 20% do dinheiro.")

    # -- dano / mortes --------------------------------------------------------------------
    def damage(self, dmg, from_pos):
        self.hp -= dmg
        self.hurt_t = 0.45
        self.since_hit = 0.0
        self.shake = min(10, self.shake + 5)
        self.burst(self.player_pos, (170, 40, 34), 5, 130)
        if self.hp <= 0:
            self.hp = 0
            self.dead_eye_on = False

    def hit_enemy(self, e, dmg):
        e.hp -= dmg
        e.alert = True
        e.hurt = 0.15
        self.burst(e.pos, (150, 34, 30), 6, 140)
        if e.hp <= 0:
            if e in self.enemies:
                self.enemies.remove(e)
            self.kills += 1
            self.mission_n += 1
            self.dead_eye = min(100, self.dead_eye + 16)
            self.pickups.append(Pickup(e.pos + V(random.uniform(-10, 10), random.uniform(-10, 10)), "money", random.randint(5, 20)))
            if random.random() < 0.6:
                self.pickups.append(Pickup(e.pos + V(random.uniform(-14, 14), random.uniform(-14, 14)), "ammo", 6))
            if random.random() < 0.15:
                self.pickups.append(Pickup(e.pos + V(random.uniform(-14, 14), random.uniform(-14, 14)), "tonic", 1))
            if self.mission_n >= self.mission_goal:
                reward = 100 * self.mission_level
                self.money += reward
                self.say("Missao %d cumprida! Recompensa: $%d" % (self.mission_level, reward))
                self.mission_level += 1
                self.mission_goal += 3
                self.mission_n = 0
        else:
            self.dead_eye = min(100, self.dead_eye + 5)

    def hit_deer(self, a, dmg):
        a.hp -= dmg
        a.flee = 3.0
        self.burst(a.pos, (150, 34, 30), 5, 120)
        if a.hp <= 0:
            if a in self.animals:
                self.animals.remove(a)
            self.pickups.append(Pickup(a.pos, "money", 9))
            self.say("Voce cacou um cervo (+$9 pela pele).")
            self.dead_eye = min(100, self.dead_eye + 6)

    # ---------------------------------------------------------------------------------------
    # Atualizacao
    # ---------------------------------------------------------------------------------------
    def update(self, real_dt):
        keys = pygame.key.get_pressed()
        alive = self.hp > 0

        # Olho Mortal
        if alive and keys[pygame.K_SPACE] and self.dead_eye > 0:
            self.dead_eye_on = True
        else:
            self.dead_eye_on = False
        slow = 0.28 if self.dead_eye_on else 1.0
        dt = real_dt * slow
        if self.dead_eye_on:
            self.dead_eye = max(0.0, self.dead_eye - 22 * real_dt)
        else:
            self.dead_eye = min(100.0, self.dead_eye + 2.0 * real_dt)

        # hora do dia
        self.time = (self.time + real_dt * 24.0 / DAY_SECONDS) % 24.0

        # temporizadores
        self.shoot_cd = max(0.0, self.shoot_cd - real_dt)
        self.flash = max(0.0, self.flash - real_dt)
        self.hurt_t = max(0.0, self.hurt_t - real_dt)
        self.since_hit += real_dt
        self.shake = max(0.0, self.shake - 22 * real_dt)
        if self.reload_t > 0:
            self.reload_t -= real_dt
            if self.reload_t <= 0:
                take = min(6 - self.ammo, self.reserve)
                self.ammo += take
                self.reserve -= take
        if alive and self.since_hit > 6 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + 1.5 * real_dt)

        # movimento do jogador
        if alive:
            move = V((keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
                     (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]))
            if move.length_squared() > 0:
                move = move.normalize()
            sprint = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            if self.mounted:
                self.horse.update_mounted(move, dt, self.world, sprint)
                self.player_pos = V(self.horse.pos)
                if self.horse.vel.length() > 170:
                    self.dust_t -= dt
                    if self.dust_t <= 0:
                        self.dust_t = 0.05
                        back = V(math.cos(self.horse.angle), math.sin(self.horse.angle)) * -34
                        self.particles.append(Particle(self.horse.pos + back, V(random.uniform(-20, 20), random.uniform(-20, 20)), 0.7, (205, 180, 135), random.uniform(4, 8)))
            elif move.length_squared() > 0:
                speed = 285 if sprint else 160
                move_with_collision(self.player_pos, move * speed * dt, 13, self.world.obstacles)
            aim = self.aim_world()
            self.player_angle = math.atan2(aim.y - self.player_pos.y, aim.x - self.player_pos.x)

        # inimigos, animais
        for e in list(self.enemies):
            e.update(dt, self)
        for a in list(self.animals):
            a.update(dt, self)

        # balas (sub-passos para nao atravessar alvos)
        alive_b = []
        for b in self.bullets:
            steps = int(b.vel.length() * dt / 12.0) + 1
            sdt = dt / steps
            gone = False
            for _ in range(steps):
                b.pos += b.vel * sdt
                b.life -= sdt
                if b.life <= 0 or not (0 <= b.pos.x < WORLD_W and 0 <= b.pos.y < WORLD_H):
                    gone = True
                    break
                if self.world.hit_obstacle((int(b.pos.x), int(b.pos.y))):
                    self.burst(b.pos, (200, 178, 134), 4, 100)
                    gone = True
                    break
                if b.owner == "p":
                    for e in self.enemies:
                        if (e.pos - b.pos).length_squared() < 17 * 17:
                            self.hit_enemy(e, b.dmg)
                            gone = True
                            break
                    if not gone:
                        for a in self.animals:
                            if (a.pos - b.pos).length_squared() < 17 * 17:
                                self.hit_deer(a, b.dmg)
                                gone = True
                                break
                elif self.hp > 0 and (self.player_pos - b.pos).length_squared() < 16 * 16:
                    self.damage(b.dmg, b.pos)
                    gone = True
                if gone:
                    break
            if not gone:
                alive_b.append(b)
        self.bullets = alive_b

        # itens
        keep = []
        for p in self.pickups:
            p.life -= real_dt
            if p.life <= 0:
                continue
            if alive and (p.pos - self.player_pos).length() < 34:
                if p.kind == "money":
                    self.money += p.val
                    self.say("+$%d" % p.val)
                elif p.kind == "ammo":
                    self.reserve += p.val
                    self.say("+%d balas" % p.val)
                else:
                    self.tonics += p.val
                    self.say("+1 tonico")
                continue
            keep.append(p)
        self.pickups = keep

        # particulas
        for p in self.particles:
            p.pos += p.vel * dt
            p.vel *= 0.92
            p.life -= dt
        self.particles = [p for p in self.particles if p.life > 0]

        # novos bandidos e animais
        self.spawn_t -= real_dt
        if self.spawn_t <= 0:
            self.spawn_t = 9.0
            if len(self.enemies) < 14 and alive:
                for _ in range(10):
                    a = random.uniform(0, math.tau)
                    d = random.uniform(850, 1100)
                    p = self.player_pos + V(math.cos(a), math.sin(a)) * d
                    if 60 < p.x < WORLD_W - 60 and 60 < p.y < WORLD_H - 60 and not self.world.blocked(p, 16) and not TOWN.collidepoint(p.x, p.y):
                        self.enemies.append(Outlaw(p, hunting=True))
                        break
            if len(self.animals) < 12:
                self.animals.append(Deer(self.random_free()))

        # mensagens
        for m in self.msgs:
            m[1] -= real_dt
        self.msgs = [m for m in self.msgs if m[1] > 0]

        # camera
        mouse = V(pygame.mouse.get_pos())
        half = V(W / 2, H / 2)
        target = self.player_pos + (mouse - half) * 0.22 - half
        self.cam += (target - self.cam) * min(1.0, 6 * real_dt)
        v = V(self.cam)
        if self.shake > 0:
            v += V(random.uniform(-1, 1), random.uniform(-1, 1)) * self.shake
        v.x = clamp(v.x, 0, WORLD_W - W)
        v.y = clamp(v.y, 0, WORLD_H - H)
        self.view = v

    # ---------------------------------------------------------------------------------------
    # Desenho
    # ---------------------------------------------------------------------------------------
    def text(self, txt, font, col, pos, anchor="topleft", shadow=True):
        img = font.render(txt, True, col)
        r = img.get_rect(**{anchor: pos})
        if shadow:
            sh = font.render(txt, True, (15, 10, 6))
            self.screen.blit(sh, r.move(2, 2))
        self.screen.blit(img, r)
        return r

    def draw_person(self, p, angle, look, flash=False, hurt=False):
        s = self.screen
        d = V(math.cos(angle), math.sin(angle))
        pygame.draw.ellipse(s, (128, 100, 66), (p.x - 13, p.y - 6, 30, 22))
        shirt = (255, 255, 255) if hurt else look["shirt"]
        pygame.draw.circle(s, shirt, (int(p.x - d.x * 2), int(p.y - d.y * 2)), 12)
        pygame.draw.circle(s, (25, 20, 18), (int(p.x - d.x * 2), int(p.y - d.y * 2)), 12, 2)
        pygame.draw.line(s, shirt, p, p + d * 16, 6)
        pygame.draw.line(s, (36, 36, 40), p + d * 13, p + d * 29, 4)
        pygame.draw.circle(s, (226, 186, 150), (int(p.x + d.x * 14), int(p.y + d.y * 14)), 4)
        if flash:
            pygame.draw.circle(s, (255, 236, 150), (int(p.x + d.x * 34), int(p.y + d.y * 34)), 9)
            pygame.draw.circle(s, (255, 255, 235), (int(p.x + d.x * 34), int(p.y + d.y * 34)), 4)
        pygame.draw.circle(s, look["band"], (int(p.x + d.x * 3), int(p.y + d.y * 3)), 11, 2)
        pygame.draw.circle(s, look["brim"], p, 11)
        pygame.draw.circle(s, look["crown"], p, 6)
        pygame.draw.circle(s, shade(look["crown"], -35), p, 6, 1)

    def draw_world(self):
        s = self.screen
        s.blit(self.world.bg, (0, 0), area=pygame.Rect(int(self.view.x), int(self.view.y), W, H))
        view = self.view
        tick = pygame.time.get_ticks()
        # fogueiras
        for c in self.world.camps:
            sp = c - view
            if -80 < sp.x < W + 80 and -80 < sp.y < H + 80:
                fl = 7 + 3 * math.sin(tick / 90.0 + c.x)
                pygame.draw.circle(s, (230, 90, 30), sp, int(fl + 3))
                pygame.draw.circle(s, (255, 170, 50), sp + V(0, -2), int(fl))
                pygame.draw.circle(s, (255, 235, 140), sp + V(0, -3), int(fl * 0.5))
        # itens
        for p in self.pickups:
            sp = p.pos - view
            if p.kind == "money":
                pygame.draw.circle(s, (120, 90, 20), sp + V(1, 2), 8)
                pygame.draw.circle(s, (240, 200, 60), sp, 7)
                pygame.draw.circle(s, (255, 235, 140), sp + V(-2, -2), 3)
            elif p.kind == "ammo":
                r = pygame.Rect(0, 0, 16, 11)
                r.center = (int(sp.x), int(sp.y))
                pygame.draw.rect(s, (90, 66, 30), r, border_radius=2)
                pygame.draw.rect(s, (200, 160, 60), r.inflate(-4, -4))
            else:
                pygame.draw.circle(s, (40, 110, 70), sp, 7)
                pygame.draw.circle(s, (150, 230, 170), sp + V(-2, -2), 3)
            if (tick // 400) % 2 == 0:
                pygame.draw.circle(s, (255, 255, 220), sp + V(7, -8), 2)
        # animais
        for a in self.animals:
            sp = a.pos - view
            img = pygame.transform.rotate(self.deer_img, -math.degrees(a.angle))
            s.blit(img, img.get_rect(center=(int(sp.x), int(sp.y))))
        # cavalo
        hp_ = self.horse.pos - view
        img = pygame.transform.rotate(self.horse_img, -math.degrees(self.horse.angle))
        s.blit(img, img.get_rect(center=(int(hp_.x), int(hp_.y))))
        # bandidos
        for e in self.enemies:
            sp = e.pos - view
            if -60 < sp.x < W + 60 and -60 < sp.y < H + 60:
                self.draw_person(sp, e.angle, e.look, e.flash > 0, e.hurt > 0)
        # jogador
        sp = self.player_pos - view
        look = {"brim": (84, 56, 30), "crown": (112, 76, 40), "shirt": (56, 88, 140), "band": (230, 200, 90)}
        if self.hp > 0:
            self.draw_person(sp, self.player_angle, look, self.flash > 0, self.hurt_t > 0.3)
        else:
            pygame.draw.ellipse(s, (60, 88, 140), (sp.x - 16, sp.y - 8, 32, 16))
            pygame.draw.circle(s, (84, 56, 30), (int(sp.x + 14), int(sp.y)), 8)
        # balas
        for b in self.bullets:
            bp = b.pos - view
            n = b.vel.normalize()
            col = (255, 240, 170) if b.owner == "p" else (255, 170, 120)
            pygame.draw.line(s, col, bp - n * 12, bp, 3)
        # particulas
        for p in self.particles:
            k = p.life / p.max
            pp = p.pos - view
            pygame.draw.circle(s, p.col, (int(pp.x), int(pp.y)), max(1, int(p.size * k)))

    def draw_light(self):
        sun = math.cos((self.time - 13.0) / 12.0 * math.pi)
        dark = clamp((0.15 - sun) / 1.15, 0.0, 1.0)
        if dark > 0.01:
            self.night.fill((8, 12, 44))
            self.night.set_alpha(int(dark * 175))
            self.screen.blit(self.night, (0, 0))
        warm = clamp(1.0 - abs(sun - 0.1) / 0.4, 0.0, 1.0)
        if warm > 0.02:
            self.warm.fill((255, 140, 60))
            self.warm.set_alpha(int(warm * 55))
            self.screen.blit(self.warm, (0, 0))
        # brilho das fogueiras a noite
        if dark > 0.15:
            tick = pygame.time.get_ticks()
            for c in self.world.camps:
                sp = c - self.view
                if -200 < sp.x < W + 200 and -200 < sp.y < H + 200:
                    glow = pygame.Surface((260, 260), pygame.SRCALPHA)
                    for r, a in ((120, 18), (80, 26), (46, 34)):
                        pygame.draw.circle(glow, (255, 150, 50, int(a * dark)), (130, 130), int(r + 4 * math.sin(tick / 120.0 + c.x)))
                    self.screen.blit(glow, (sp.x - 130, sp.y - 130))

    def bar(self, x, y, w, h, frac, col, label):
        s = self.screen
        pygame.draw.rect(s, (18, 12, 8), (x - 3, y - 3, w + 6, h + 6), border_radius=5)
        pygame.draw.rect(s, (62, 46, 30), (x, y, w, h), border_radius=3)
        if frac > 0:
            pygame.draw.rect(s, col, (x, y, int(w * clamp(frac, 0, 1)), h), border_radius=3)
        self.text(label, self.f_tiny, (245, 232, 200), (x + 6, y + h // 2), "midleft")

    def draw_hud(self):
        s = self.screen
        # dano
        if self.hurt_t > 0:
            red = pygame.Surface((W, H), pygame.SRCALPHA)
            red.fill((160, 0, 0, int(110 * self.hurt_t / 0.45)))
            s.blit(red, (0, 0))
        if self.hp < 35 and self.hp > 0:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 160.0)
            red = pygame.Surface((W, H), pygame.SRCALPHA)
            red.fill((140, 0, 0, int(45 * pulse)))
            s.blit(red, (0, 0))
        # barras
        self.bar(28, H - 64, 270, 18, self.hp / self.max_hp, (176, 46, 40) if self.hp > 35 else (220, 40, 30), "SAUDE")
        self.bar(28, H - 34, 270, 12, self.dead_eye / 100.0, (224, 180, 70) if not self.dead_eye_on else (255, 220, 120), "OLHO MORTAL")
        # municao
        base = (W - 40, H - 40)
        self.text("%d" % self.ammo, self.f_l, (245, 232, 200), (base[0] - 90, base[1]), "bottomright")
        self.text("/ %d" % self.reserve, self.f_m, (210, 190, 150), (base[0], base[1] - 6), "bottomright")
        for i in range(6):
            c = (W - 220 + i * 22, H - 118)
            pygame.draw.circle(s, (20, 14, 10), c, 9)
            pygame.draw.circle(s, (232, 190, 80) if i < self.ammo else (70, 54, 38), c, 7)
        self.text("Tonicos: %d  [Q]" % self.tonics, self.f_s, (180, 235, 190), (W - 40, H - 140), "bottomright")
        # topo-esquerda
        self.text("$ %d" % self.money, self.f_m, (240, 205, 90), (24, 18))
        self.text("Missao %d: elimine bandidos (%d/%d)" % (self.mission_level, self.mission_n, self.mission_goal), self.f_s, (245, 232, 200), (24, 52))
        self.text("Bandidos abatidos: %d" % self.kills, self.f_s, (210, 190, 150), (24, 74))
        # relogio
        hh = int(self.time)
        mm = int((self.time - hh) * 60)
        self.text("%02d:%02d" % (hh, mm), self.f_m, (245, 232, 200), (W // 2, 14), "midtop")
        # mensagens
        y = 110
        for t, life in self.msgs:
            a = clamp(life / 1.0, 0, 1)
            col = tuple(int(c * (0.4 + 0.6 * a)) for c in (245, 232, 200))
            self.text(t, self.f_s, col, (24, y))
            y += 22
        # minimapa
        mx, my = W - MM_W - 18, 18
        s.blit(self.world.mini, (mx, my))
        k = MM_W / float(WORLD_W)
        for e in self.enemies:
            if e.alert or self.dead_eye_on:
                pygame.draw.circle(s, (220, 50, 40), (int(mx + e.pos.x * k), int(my + e.pos.y * k)), 2)
        pygame.draw.circle(s, (130, 76, 36), (int(mx + self.horse.pos.x * k), int(my + self.horse.pos.y * k)), 3)
        pygame.draw.circle(s, (255, 255, 255), (int(mx + self.player_pos.x * k), int(my + self.player_pos.y * k)), 3)
        pygame.draw.rect(s, (240, 220, 160), (mx + self.view.x * k, my + self.view.y * k, W * k, H * k), 1)
        pygame.draw.rect(s, (30, 20, 12), (mx - 2, my - 2, MM_W + 4, MM_H + 4), 3)
        # dica de montaria
        if self.hp > 0:
            if self.mounted:
                self.text("[E] Desmontar", self.f_m, (255, 240, 200), (W // 2, H - 90), "midbottom")
            elif (self.horse.pos - self.player_pos).length() < 90:
                self.text("[E] Montar no cavalo", self.f_m, (255, 240, 200), (W // 2, H - 90), "midbottom")

    def draw_deadeye(self):
        self.screen.blit(self.sepia, (0, 0))
        for e in self.enemies:
            sp = e.pos - self.view
            if -40 < sp.x < W + 40 and -40 < sp.y < H + 40 and (e.pos - self.player_pos).length() < 800:
                pygame.draw.circle(self.screen, (230, 50, 40), sp, 20, 2)
                pygame.draw.line(self.screen, (230, 50, 40), sp - V(26, 0), sp - V(14, 0), 2)
                pygame.draw.line(self.screen, (230, 50, 40), sp + V(14, 0), sp + V(26, 0), 2)

    def draw_crosshair(self):
        m = V(pygame.mouse.get_pos())
        s = self.screen
        col = (255, 90, 70) if self.dead_eye_on else (250, 240, 215)
        pygame.draw.circle(s, col, m, 13, 2)
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(s, col, m + V(d) * 6, m + V(d) * 20, 2)
        pygame.draw.circle(s, col, m, 2)
        if self.reload_t > 0:
            frac = 1 - self.reload_t / 1.5
            pygame.draw.rect(s, (20, 14, 8), (m.x - 26, m.y + 24, 52, 8))
            pygame.draw.rect(s, (230, 190, 80), (m.x - 25, m.y + 25, int(50 * frac), 6))

    def draw_play(self):
        self.draw_world()
        self.draw_light()
        if self.dead_eye_on:
            self.draw_deadeye()
            self.vignette.set_alpha(255)
        else:
            self.vignette.set_alpha(110)
        self.screen.blit(self.vignette, (0, 0))
        self.draw_hud()
        if self.hp <= 0:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((70, 0, 0, 150))
            self.screen.blit(ov, (0, 0))
            self.text("VOCE MORREU", self.f_xl, (200, 40, 34), (W // 2, H // 2 - 50), "center")
            self.text("Pressione R para renascer na cidade (perde 20% do dinheiro)", self.f_m, (245, 232, 200), (W // 2, H // 2 + 30), "center")
        if self.paused:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 140))
            self.screen.blit(ov, (0, 0))
            self.text("PAUSADO", self.f_xl, (245, 232, 200), (W // 2, H // 2), "center")
        self.draw_crosshair()

    def draw_menu(self):
        s = self.screen
        s.blit(self.menu_bg, (0, 0))
        self.text("FRONTEIRA SELVAGEM", self.f_xl, (255, 226, 150), (W // 2, 130), "center")
        self.text("Um faroeste de mundo aberto em Pygame", self.f_m, (255, 236, 200), (W // 2, 200), "center")
        lines = ["WASD / Setas  -  andar            SHIFT  -  correr / galopar",
                 "Mouse  -  mirar            Clique  -  atirar            R  -  recarregar",
                 "ESPACO  -  Olho Mortal (camera lenta + mira automatica)",
                 "E  -  montar / desmontar            Q  -  tonico            P  -  pausar"]
        for i, l in enumerate(lines):
            self.text(l, self.f_s, (255, 240, 210), (W // 2, 300 + i * 28), "center")
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            self.text("Pressione ENTER para comecar", self.f_m, (255, 255, 255), (W // 2, 460), "center")
        m = V(pygame.mouse.get_pos())
        pygame.draw.circle(s, (250, 240, 215), m, 12, 2)
        pygame.draw.circle(s, (250, 240, 215), m, 2)

    # ---------------------------------------------------------------------------------------
    def run(self):
        while True:
            real_dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if self.state == "menu":
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                            self.state = "play"
                    else:
                        if ev.key == pygame.K_p:
                            self.paused = not self.paused
                        elif not self.paused:
                            if ev.key == pygame.K_r:
                                if self.hp <= 0:
                                    self.respawn()
                                else:
                                    self.start_reload()
                            elif ev.key == pygame.K_e:
                                self.toggle_mount()
                            elif ev.key == pygame.K_q:
                                self.use_tonic()
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self.state == "play" and not self.paused:
                        self.shoot()
            if self.state == "menu":
                self.draw_menu()
            else:
                if not self.paused:
                    self.update(real_dt)
                self.draw_play()
            pygame.display.flip()


if __name__ == "__main__":
    Game().run()