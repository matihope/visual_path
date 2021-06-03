import pygame
import time
import threading
import ui_elements as UI
import json

pygame.init()


class Tile(UI.Label):
    def __init__(self, x, y, size, text: str = '', **kwargs):
        super().__init__(x, y, text=text, **kwargs)
        self.width = size
        self.height = size
        self.size = size
        self.size_buffer = 1
        self.color = (75, 75, 75)

        self._tile_type = ''
        self.tile_type = kwargs.get('tile_type', '')

    @property
    def tile_type(self) -> str:
        return self._tile_type

    @tile_type.setter
    def tile_type(self, value: str) -> None:
        self._tile_type = value
        if value == '':  # default
            self.color = GLOBALS['TILE_COLOR_TYPE_DEFAULT']

        else:
            self.color = GLOBALS[f'TILE_COLOR_TYPE_{value}']

    def draw(self, surface):
        pygame.draw.rect(surface, GLOBALS['TILE_BORDER_COLOR'], (self.x, self.y, self.size, self.size))
        pygame.draw.rect(
            surface,
            self.color, (
                self.x + self.size_buffer,
                self.y + self.size_buffer,
                self.size - 2 * self.size_buffer,
                self.size - 2 * self.size_buffer
            )
        )
        surface.blit(self.text_obj, self.text_pos)

    def check_collision(self, point: tuple[float, float]) -> bool:
        rounded_point = (
            point[0] // self.size * self.size,
            point[1] // self.size * self.size
        )
        return rounded_point == (self.x, self.y)

    def update(self, keys, mouse, dt) -> None:
        if mouse.get_pressed()[0]:
            if self.check_collision(mouse.get_pos()):
                self.tile_type = 'BLOCK'
        elif mouse.get_pressed()[1]:
            if self.check_collision(mouse.get_pos()):
                self.tile_type = ''
        elif mouse.get_pressed()[2]:
            if self.check_collision(mouse.get_pos()):
                self.tile_type = 'TARGET'

    def __repr__(self) -> str:
        return '{}({}, {}, {})'.format(
            __class__.__name__,
            self.x // self.size,
            self.y // self.size,
            self.tile_type
        )


class Game:
    def __init__(self, size):
        self._size = size
        self.tile_size = GLOBALS['HEIGHT'] // size
        self.tiles = []
        self.size = size
        self.path_algs = [self.bfs]
        self.path_alg_indx = 0
        self.t = threading.Thread()

        self.ui_elements = []

        # UI
        self.font = pygame.font.SysFont('', round(48 * GLOBALS['HEIGHT'] / 1000 * 20 / self.size))
        UI_FONT_COLOR = GLOBALS['UI_FONT_COLOR']

        def start_search(button, pressed):
            self.find_path()
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            10,
            250,
            50,
            f'Start search (SPACE)',
            action=start_search,
            font_color=(UI_FONT_COLOR),
            colors=GLOBALS['UI_START_SEARCH_BUTTON_COLORS'],
            anchor_x='center',
            anchor_y='top'
        ))

        def reset_search(button, pressed):
            self.reset()
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            70,
            250,
            50,
            f'Reset search (R)',
            action=reset_search,
            font_color=(UI_FONT_COLOR),
            colors=GLOBALS['UI_RESET_SEARCH_BUTTON_COLORS'],
            anchor_x='center',
            anchor_y='top'
        ))

        def change_path_finding_method(button, pressed):
            self.path_alg_indx += pressed[0] - pressed[1]
            self.path_alg_indx %= len(self.path_algs)
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            GLOBALS['HEIGHT'] - 310,
            300,
            50,
            f'Method: {self.path_algs[self.path_alg_indx].__name__}',
            action=change_path_finding_method,
            font_color=(UI_FONT_COLOR),
            colors=GLOBALS['UI_METHOD_BUTTON_COLORS'],
            anchor_x='center',
            anchor_y='bottom'
        ))

        def change_path_draw_time(button, pressed):
            GLOBALS['PATH_DRAW_TIME'] += 0.25 * (pressed[0] - pressed[2])
            GLOBALS['PATH_DRAW_TIME'] = round(GLOBALS['PATH_DRAW_TIME'], 3)
            GLOBALS['PATH_DRAW_TIME'] %= 20
            if pressed[1]:
                GLOBALS['PATH_DRAW_TIME'] = 0
            button.text = f'Path draw time: {GLOBALS["PATH_DRAW_TIME"]}s'
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            GLOBALS['HEIGHT'] - 250,
            300,
            50,
            f'Path draw time: {GLOBALS["PATH_DRAW_TIME"]}s',
            action=change_path_draw_time,
            font_color=(UI_FONT_COLOR),
            colors=GLOBALS['UI_BUTTON_COLORS'],
            anchor_x='center',
            anchor_y='bottom',
            long_press=True
        ))

        def change_grid_size(button, pressed):
            if self.t.is_alive():
                return
            self.size %= 100
            self.size += 1 * (pressed[0] - pressed[2])
            self.size = max(2, self.size)
            button.text = f'Grid size: {self.size}x{self.size}'
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            GLOBALS['HEIGHT'] - 190,
            300,
            50,
            f'Grid size: {self.size}x{self.size}',
            action=change_grid_size,
            font_color=(UI_FONT_COLOR),
            colors=GLOBALS['UI_BUTTON_COLORS'],
            anchor_x='center',
            anchor_y='bottom',
            long_press=True
        ))

        def change_pause_time(button, pressed):
            if GLOBALS['PAUSE_TIME'] > 0.005:
                GLOBALS['PAUSE_TIME'] += 0.005 * (pressed[0] - pressed[2])
                button.text = f'Pause time: {round(GLOBALS["PAUSE_TIME"], 3)}s'
            else:
                GLOBALS['PAUSE_TIME'] += 0.0001 * (pressed[0] - pressed[2])
                button.text = f'Pause time: {round(GLOBALS["PAUSE_TIME"], 4)}s'
            GLOBALS['PAUSE_TIME'] %= 0.500

            if pressed[1]:
                GLOBALS['PAUSE_TIME'] = 0
                button.text = f'Pause time: {round(GLOBALS["PAUSE_TIME"], 1)}s'
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            GLOBALS['HEIGHT'] - 130,
            300,
            50,
            f'Pause time: {GLOBALS["PAUSE_TIME"]}s',
            action=change_pause_time,
            font_color=(UI_FONT_COLOR),
            colors=GLOBALS['UI_BUTTON_COLORS'],
            anchor_x='center',
            anchor_y='bottom',
            long_press=True
        ))

        def set_diagonally_btn_txt(button, pressed):
            if self.t.is_alive():
                return
            GLOBALS['DIAGONALLY'] = not GLOBALS['DIAGONALLY']
            button.text = f'Diagonal connections: {GLOBALS["DIAGONALLY"]}'
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            GLOBALS['HEIGHT'] - 70,
            300,
            50,
            f'Diagonal connections: {GLOBALS["DIAGONALLY"]}',
            action=set_diagonally_btn_txt,
            font_color=(UI_FONT_COLOR),
            colors=GLOBALS['UI_BUTTON_COLORS'],
            anchor_x='center',
            anchor_y='bottom'
        ))

        def clear_board(button, pressed):
            self.generate()
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            GLOBALS['HEIGHT'] - 10,
            200,
            50,
            f'Clear the board',
            action=clear_board,
            font_color=(UI_FONT_COLOR),
            colors=GLOBALS['UI_BUTTON_COLORS'],
            anchor_x='center',
            anchor_y='bottom'
        ))

    def draw(self, surface):
        for line in self.tiles:
            for tile in line:
                tile.draw(surface)

        for el in self.ui_elements:
            el.draw(surface)

    def update(self, keys, mouse, dt):
        for line in self.tiles:
            for tile in line:
                tile.update(keys, mouse, dt)

        for el in self.ui_elements:
            el.update(keys, mouse, dt)

    @property
    def size(self) -> int:
        return self._size

    @size.setter
    def size(self, value: int) -> None:
        self._size = value
        self.font = pygame.font.SysFont('', round(48 * GLOBALS['HEIGHT'] / 1000 * 20 / self.size))
        self.tile_size = GLOBALS['HEIGHT'] // self._size
        self.generate()

    def generate(self):
        self.tiles = []
        for x in range(self.size):
            line = []
            for y in range(self.size):
                tile = Tile(
                    x * self.tile_size,
                    y * self.tile_size,
                    self.tile_size,
                    font=self.font,
                    font_color=GLOBALS['BOARD_FONT_COLOR'])
                line.append(tile)
            self.tiles.append(line)

    def reset(self):
        if self.t.is_alive():
            return

        for line in self.tiles:
            for tile in line:
                tile.text = ''
                if tile.tile_type == 'VISITED' or tile.tile_type == 'PATH':
                    tile.tile_type = ''

    def find_path(self):
        if self.t.is_alive():
            return
        self.reset()

        t_blocks = []
        for line in self.tiles:
            for tile in line:
                if tile.tile_type == 'TARGET':
                    t_blocks.append(tile)
        if len(t_blocks) != 2:
            print('Make sure, amount of TARGET-type blocks == 2')
            return

        start, end = t_blocks
        print(f'Seaching path from: {start} to {end}...')
        self.t = threading.Thread(target=self.path_algs[self.path_alg_indx],
                                  args=(start, end))
        self.t.start()

    def bfs(self, start, end):
        queue = [start]
        distance = {start: 0}
        parent = {start: None}
        end_reached = False

        while queue and not end_reached:
            u = queue.pop(0)
            node_x = u.x // u.size
            node_y = u.y // u.size
            for x in range(-1, 2):
                for y in range(-1, 2):
                    if abs(x) == abs(y) and not GLOBALS['DIAGONALLY']:
                        continue

                    if node_x + x in range(self.size):
                        if node_y + y in range(self.size):
                            new_node = self.tiles[node_x + x][node_y + y]
                            if new_node.tile_type == '' or new_node == end:
                                queue.append(new_node)

                                if new_node != end:
                                    new_node.tile_type = 'VISITED'
                                else:
                                    end_reached = True

                                distance[new_node] = distance[u] + 1
                                parent[new_node] = u
                            time.sleep(GLOBALS['PAUSE_TIME'])

        def enter_and_mark(node):
            if parent.get(node):
                if node.tile_type == 'VISITED':
                    time.sleep(GLOBALS['PATH_DRAW_TIME']/distance[end])
                    node.tile_type = 'PATH'
                    node.text = distance[node]

                enter_and_mark(parent[node])
        end.text = distance.get(end)
        enter_and_mark(end)


def main():
    run = True
    clock = pygame.time.Clock()
    game1 = Game(20)
    while run:
        dt = clock.tick(GLOBALS['FPS'])
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                GLOBALS['PAUSE_TIME'] = 0

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    game1.find_path()
                if event.key == pygame.K_r:
                    game1.reset()

        win.fill(GLOBALS['BACKGROUND_COLOR'])
        game1.update(pygame.key.get_pressed(), pygame.mouse, dt)
        game1.draw(win)
        pygame.display.flip()


if __name__ == "__main__":
    with open('variables.json') as json_file:
        GLOBALS = json.load(json_file)

    UI_START_X = GLOBALS['HEIGHT']
    UI_START_Y = 0
    UI_WIDTH = GLOBALS['WIDTH'] - GLOBALS['HEIGHT']
    UI_HEIGHT = GLOBALS['HEIGHT']

    win = pygame.display.set_mode((GLOBALS['WIDTH'], GLOBALS['HEIGHT']))
    pygame.display.set_caption("Visual Path V0.1")
    main()
