import pygame
import time
import threading
import ui_elements as UI
import json
import re

pygame.init()

with open('variables.json') as json_file:
    GLOBALS = json.load(json_file)


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
        pygame.draw.rect(
            surface, GLOBALS['TILE_BORDER_COLOR'], (self.x, self.y, self.size, self.size))
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

    def update(self, keys, mouse, dt, events) -> None:
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
        self.path_algs = [self.bfs, self.a_star]
        self.path_alg_indx = 0
        self.t = threading.Thread()

        self.ui_elements = []
        self.board_button_manager = UI.BoardButtonManager(self, GLOBALS['BOARDS_FOLDER'])
        self.boards_buttons = []
        self.show_screen_index = 0
        self.screen_elements = [
            [self.ui_elements, self.tiles],  # main screen
            # screen for choosing boards
            [self.board_button_manager, self.boards_buttons],
        ]

        # UI
        self.font = pygame.font.SysFont(
            '', round(48 * GLOBALS['HEIGHT'] / 1000 * 20 / self.size))
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

        self.board_name_input = UI.TextInput(
            UI_START_X + UI_WIDTH // 2,
            GLOBALS['HEIGHT'] - 490,
            300,
            50,
            placeholder='Board name...',
            anchor_x='center',
            anchor_y='bottom'
        )
        self.ui_elements.append(self.board_name_input)

        def save_board(button, pressed):
            if filename := self.board_name_input.current_text:
                self.save_board(filename)
            else:
                print('You have to input a board name in the input box in order to save!')
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            GLOBALS['HEIGHT'] - 430,
            300,
            50,
            f'Save the board',
            action=save_board,
            font_color=(UI_FONT_COLOR),
            anchor_x='center',
            anchor_y='bottom'
        ))

        def choose_boards(button, pressed):
            self.board_button_manager.load_boards()
            self.show_screen_index = 1
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            GLOBALS['HEIGHT'] - 370,
            300,
            50,
            f'Choose a board',
            action=choose_boards,
            font_color=(UI_FONT_COLOR),
            anchor_x='center',
            anchor_y='bottom'
        ))

        def change_path_finding_method(button, pressed):
            if self.t.is_alive():
                return
            self.path_alg_indx += pressed[0] - pressed[1]
            self.path_alg_indx %= len(self.path_algs)
            button.text = f'Method: {self.path_algs[self.path_alg_indx].__name__}'
            if self.path_algs[self.path_alg_indx] == self.a_star:
                GLOBALS['DIAGONALLY'] = True
                print('Diagonal setting is ignored in order for A* to work properly')
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

        # Board choose screen
        def go_back(button, pressed):
            self.show_screen_index = 0
        self.boards_buttons.append(UI.Button(
            GLOBALS['WIDTH']//2 - 10,
            GLOBALS['HEIGHT']-25,
            200,
            50,
            'Back',
            action=go_back,
            anchor_x='right',
            anchor_y='bottom'
        ))

        def create_new_board(button, pressed):
            self.show_screen_index = 0
            self.board_name_input.current_text = ''
            self.size = size
            self.reset()
        self.boards_buttons.append(UI.Button(
            GLOBALS['WIDTH']//2 + 10,
            GLOBALS['HEIGHT']-25,
            200,
            50,
            'New board',
            action=create_new_board,
            anchor_x='left',
            anchor_y='bottom'
        ))

        # finally, load the default board to the screen
        if GLOBALS['LOAD_DEAFULT_BOARD_ON_STARTUP']:
            try:
                self.load_board('default_board')
            except ValueError as e:
                print("There is no default board!")

    def draw(self, surface):
        def perform_draw(item):
            if type(item) == list:
                for el in item:
                    perform_draw(el)
            else:
                item.draw(surface)

        for item in self.screen_elements[self.show_screen_index]:
            perform_draw(item)

    def update(self, keys, mouse, dt, events):
        def perform_update(item):
            if type(item) == list:
                for el in item:
                    perform_update(el)
            else:
                item.update(keys, mouse, dt, events)

        for item in self.screen_elements[self.show_screen_index]:
            perform_update(item)

    @property
    def size(self) -> int:
        return self._size

    @size.setter
    def size(self, value: int) -> None:
        self._size = value
        self.font = pygame.font.SysFont(
            '', round(48 * GLOBALS['HEIGHT'] / 1000 * 20 / self.size))
        self.tile_size = GLOBALS['HEIGHT'] // self._size
        self.generate()

    def generate(self):
        self.tiles.clear()
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
                if 'VISITED' in tile.tile_type or tile.tile_type == 'PATH':
                    tile.tile_type = ''

    def load_board(self, board_name):
        self.board_name_input.current_text = board_name
        with open(f'boards/{board_name}.pth', 'r') as board:
            content = board.readlines()
            self.size = int(content.pop(0))
            p = re.compile(
                r'Tile\((?P<x>[0-9]+), (?P<y>[0-9]+), (?P<tile_type>[A-Z]+)\)')
            for tile in content:
                m = p.match(tile)
                self.tiles[int(m.group('x'))][int(m.group('y'))
                                              ].tile_type = m.group('tile_type')

    def save_board(self, filename):
        with open(f'boards/{filename}.pth', 'w') as board:
            board.write(str(self.size) + '\n')
            for line in self.tiles:
                for tile in line:
                    if tile.tile_type == 'BLOCK' or tile.tile_type == 'TARGET':
                        board.write(str(tile) + "\n")

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
        visited = {start: True}
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
                            if not visited.get(new_node) and new_node.tile_type != "BLOCK":
                                queue.append(new_node)

                                if new_node != end:
                                    new_node.tile_type = 'VISITED'
                                    visited[new_node] = True
                                else:
                                    end_reached = True

                                distance[new_node] = distance[u] + 1
                                parent[new_node] = u
                                time.sleep(GLOBALS['PAUSE_TIME'])

        def enter_and_mark(node):
            if parent.get(node):
                time.sleep(GLOBALS['PATH_DRAW_TIME']/distance[end])
                if 'VISITED' in node.tile_type:
                    node.tile_type = 'PATH'
                node.text = distance[node]

                enter_and_mark(parent[node])
        enter_and_mark(end)

    def a_star(self, start, end):
        g_cost = {start: 0}  # distance from start node
        h_cost = {end: 0}  # distance from end node
        f_cost = {}  # sum of g_cost and h_cost
        closed = {start: False}  # if node is done with its neighbors
        parent = {start: None}
        h = [start]  # priority queue
        end_reached = False

        # preprocess the g_cost for every node
        queue = [end]
        mini_visited = {}
        while queue:
            u = queue.pop(0)
            node_x = u.x // u.size
            node_y = u.y // u.size
            mini_visited[u] = True
            for x in range(-1, 2):
                for y in range(-1, 2):
                    if x != 0 or y != 0:
                        if node_x + x in range(self.size):
                            if node_y + y in range(self.size):
                                new_node = self.tiles[node_x + x][node_y + y]
                                if not mini_visited.get(new_node) and new_node not in queue:
                                    queue.append(new_node)
                                if abs(x) == abs(y):  # diagonal
                                    if h_cost.get(new_node, -1) == -1 or \
                                       h_cost[new_node] > h_cost[u] + 14:
                                        h_cost[new_node] = h_cost[u] + 14
                                else:
                                    if h_cost.get(new_node, -1) == -1 or \
                                       h_cost[new_node] > h_cost[u] + 10:
                                        h_cost[new_node] = h_cost[u] + 10

        while h and not end_reached:
            node = h.pop(-1)
            node_x = node.x // node.size
            node_y = node.y // node.size
            closed[node] = True
            if node != start and node != end:
                node.tile_type = 'VISITED'
            for x in range(-1, 2):
                for y in range(-1, 2):
                    if x != 0 or y != 0:
                        if node_x + x in range(self.size):
                            if node_y + y in range(self.size):
                                new_node = self.tiles[node_x + x][node_y + y]
                                if not closed.get(new_node) and new_node.tile_type != 'BLOCK':
                                    time.sleep(GLOBALS['PAUSE_TIME'])
                                    if new_node != end:
                                        new_node.tile_type = 'VISITED_ALTERNATIVE'
                                    if new_node == end:
                                        end_reached = True
                                    if abs(x) == abs(y):  # diagonal move
                                        if g_cost.get(new_node, -1) == -1 or \
                                           g_cost[new_node] > g_cost[node] + 14:
                                            g_cost[new_node] = g_cost[node] + 14
                                            parent[new_node] = node
                                    else:  # vertical or horizontal move
                                        if g_cost.get(new_node, -1) == -1 or \
                                           g_cost[new_node] > g_cost[node] + 10:
                                            g_cost[new_node] = g_cost[node] + 10
                                            parent[new_node] = node
                                    f_cost[new_node] = g_cost[new_node] + \
                                        h_cost[new_node]
                                    if new_node not in h:
                                        h.append(new_node)
                                        h.sort(key=lambda x: -f_cost[x])

        path_tiles = []

        def draw_path(node):
            if node == start:
                return
            path_tiles.append(node)
            draw_path(parent[node])

        if parent.get(end):
            # path extists
            draw_path(parent[end])
            end.text = len(path_tiles) + 1
        else:
            # path doesn't exist
            end.text = "-1"

        for i, tile in enumerate(path_tiles):
            tile.tile_type = 'PATH'
            tile.text = len(path_tiles) - i
            time.sleep(GLOBALS['PATH_DRAW_TIME']/len(path_tiles))


def main():
    run = True
    clock = pygame.time.Clock()
    game1 = Game(20)
    while run:
        dt = clock.tick(GLOBALS['FPS'])
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                run = False
                GLOBALS['PAUSE_TIME'] = 0
                GLOBALS['PATH_DRAW_TIME'] = 0

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    game1.find_path()
                if event.key == pygame.K_r:
                    game1.reset()

        win.fill(GLOBALS['BACKGROUND_COLOR'])
        game1.update(pygame.key.get_pressed(), pygame.mouse, dt, events)
        game1.draw(win)
        pygame.display.flip()


if __name__ == "__main__":
    GLOBALS['WIDTH'] = int(GLOBALS['WIDTH'] * GLOBALS['WINDOW_SCALE'])
    GLOBALS['HEIGHT'] = int(GLOBALS['HEIGHT'] * GLOBALS['WINDOW_SCALE'])
    UI_START_X = GLOBALS['HEIGHT']
    UI_START_Y = 0
    UI_WIDTH = GLOBALS['WIDTH'] - GLOBALS['HEIGHT']
    UI_HEIGHT = GLOBALS['HEIGHT']

    win = pygame.display.set_mode((GLOBALS['WIDTH'], GLOBALS['HEIGHT']))
    pygame.display.set_caption("Visual Path V0.2")
    main()
