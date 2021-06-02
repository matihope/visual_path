import pygame
import time
import threading
import ui_elements as UI

pygame.init()

WIDTH, HEIGHT = 1000, 600
UI_START_X = HEIGHT
UI_START_Y = 0
UI_WIDTH = WIDTH - HEIGHT
UI_HEIGHT = HEIGHT

FONT = pygame.font.SysFont('', round(48 * HEIGHT / 1000))
FPS = 60
PAUSE_TIME = 0.005
DIAGONALLY = False
FONT_COLOR = (255, 112, 150)


class Tile(UI.Label):
    def __init__(self, x, y, size, tile_type: str = '', text: str = ''):
        super().__init__(x, y, text)
        self.width = size
        self.height = size
        self.size = size
        self.size_buffer = 1
        self.color = (75, 75, 75)

        self._tile_type = ''
        self.tile_type = tile_type

    @property
    def tile_type(self) -> str:
        return self._tile_type

    @tile_type.setter
    def tile_type(self, value: str) -> None:
        self._tile_type = value
        if value == '':  # default
            self.color = (69, 123, 157)

        if value == 'B':  # block type, like wall
            self.color = (230, 57, 70)

        if value == 'T':  # target type
            self.color = (118, 200, 147)

        if value == 'V':  # visited type
            self.color = (168, 218, 220)

        if value == 'P':  # path type
            self.color = (233, 196, 106)

    def draw(self, surface):
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

    def update(self, keys, mouse) -> None:
        if mouse.get_pressed()[0]:
            if self.check_collision(mouse.get_pos()):
                self.tile_type = 'B'
        elif mouse.get_pressed()[1]:
            if self.check_collision(mouse.get_pos()):
                self.tile_type = ''
        elif mouse.get_pressed()[2]:
            if self.check_collision(mouse.get_pos()):
                self.tile_type = 'T'

    def __repr__(self) -> str:
        return '{}({}, {}, {})'.format(
            __class__.__name__,
            self.x // self.size,
            self.y // self.size,
            self.tile_type
        )


class Game:
    def __init__(self, size):
        self.size = size
        self.tile_size = HEIGHT // self.size
        self.tiles = []
        self.generate()
        self.path_finding_method = self.bfs
        self.t = threading.Thread()

        self.ui_elements = []

        def set_diagonally_btn_txt(button):
            global DIAGONALLY
            DIAGONALLY = not DIAGONALLY
            button.text = f'Diagonal connections: {DIAGONALLY}'
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            25,
            300,
            50,
            f'Diagonal connections: {DIAGONALLY}',
            action=set_diagonally_btn_txt,
            font_color=(247, 37, 133),
            anchor_x='center',
            anchor_y='top'
        ))

        def reset_search(button):
            self.reset()
        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            100,
            100,
            50,
            f'Reset (R)',
            action=reset_search,
            font_color=(247, 37, 133),
            anchor_x='center',
            anchor_y='top'
        ))

        def start_search(button):
            self.find_path()

        self.ui_elements.append(UI.Button(
            UI_START_X + UI_WIDTH // 2,
            175,
            250,
            50,
            f'Start search (SPACE)',
            action=start_search,
            font_color=(247, 37, 133),
            anchor_x='center',
            anchor_y='top'
        ))

    def draw(self, surface):
        for line in self.tiles:
            for tile in line:
                tile.draw(surface)

        for el in self.ui_elements:
            el.draw(surface)

    def update(self, keys, mouse):
        for line in self.tiles:
            for tile in line:
                tile.update(keys, mouse)

        for el in self.ui_elements:
            el.update(keys, mouse)

    def generate(self):
        for x in range(self.size):
            line = []
            for y in range(self.size):
                tile = Tile(x * self.tile_size, y * self.tile_size, self.tile_size)
                line.append(tile)
            self.tiles.append(line)

    def reset(self):
        if self.t.is_alive():
            return

        for line in self.tiles:
            for tile in line:
                tile.text = ''
                if tile.tile_type == 'V' or tile.tile_type == 'P':
                    tile.tile_type = ''

    def find_path(self):
        if self.t.is_alive():
            return
        self.reset()

        t_blocks = []
        for line in self.tiles:
            for tile in line:
                if tile.tile_type == 'T':
                    t_blocks.append(tile)
        if len(t_blocks) != 2:
            print('Make sure, amount of TARGET-type blocks == 2')
            return

        start, end = t_blocks
        print(f'Seaching path from: {start} to {end}...')
        self.t = threading.Thread(target=self.path_finding_method, args=(start, end))
        self.t.start()

    def bfs(self, start, end):
        queue = [start]
        distance = {start: 0}
        parent = {start: None}
        # start = 'V'
        end_reached = False

        while queue and not end_reached:
            u = queue.pop(0)
            node_x = u.x // u.size
            node_y = u.y // u.size
            for x in range(-1, 2):
                for y in range(-1, 2):
                    if abs(x) == abs(y) and not DIAGONALLY:
                        continue

                    if node_x + x in range(self.size):
                        if node_y + y in range(self.size):
                            new_node = self.tiles[node_x + x][node_y + y]
                            if new_node.tile_type == '' or new_node == end:
                                queue.append(new_node)

                                if new_node != end:
                                    new_node.tile_type = 'V'
                                else:
                                    end_reached = True

                                distance[new_node] = distance[u] + 1
                                parent[new_node] = u

            time.sleep(PAUSE_TIME)

        def enter_and_mark(node):
            if parent.get(node):
                if node.tile_type == 'V':
                    node.tile_type = 'P'
                    node.text = distance[node]

                enter_and_mark(parent[node])
        enter_and_mark(end)
        end.text = distance.get(end)


def main():
    run = True
    clock = pygame.time.Clock()
    game1 = Game(20)
    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                global PAUSE_TIME
                run = False
                PAUSE_TIME = 0

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    game1.find_path()
                if event.key == pygame.K_r:
                    game1.reset()

        win.fill((29, 53, 87))
        game1.update(pygame.key.get_pressed(), pygame.mouse)
        game1.draw(win)
        pygame.display.flip()


if __name__ == "__main__":
    win = pygame.display.set_mode((WIDTH, HEIGHT))
    main()
