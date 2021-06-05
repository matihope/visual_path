import pygame
import re
import os

pygame.font.init()
DEFAULT_FONT = pygame.font.SysFont('', 28)
DEFAULT_FONT_COLOR = (255, 255, 255)


class Label:
    def __init__(self, x, y, text, width=0, height=0, **kwargs):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        self.font = kwargs.get('font', DEFAULT_FONT)
        self.font_color = kwargs.get('font_color', DEFAULT_FONT_COLOR)

        self._text = ''
        self.text_obj = None
        self.text_pos = ()
        self.text = text

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value) -> None:
        self._text = str(value)
        self.text_obj = self.font.render(self._text, True, self.font_color)
        self.text_pos = (self.x + self.width // 2 - self.text_obj.get_width() // 2,
                         self.y + self.height // 2 - self.text_obj.get_height() // 2)


class Button(Label):
    def __init__(self, x, y, width, height, text, action=None,
                 colors=((160, 26, 88), (114, 60, 112), (69, 94, 137)),
                 anchor_x='center', anchor_y='center', **kwargs):

        if anchor_x == 'left':
            pass
        elif anchor_x == 'center':
            x -= width // 2
        elif anchor_x == 'right':
            x -= width

        if anchor_y == 'top':
            pass
        elif anchor_y == 'center':
            y -= height // 2
        elif anchor_y == 'bottom':
            y -= height

        super().__init__(x, y, text, width, height, **kwargs)
        self.colors = colors
        self.color = self.colors[0]
        self.action = action
        self.pressed_before = False
        self.pressed_before_buttons: tuple[bool, bool, bool]
        self.long_press = kwargs.get('long_press', False)
        self.tick_time = kwargs.get('tick_time', 0.1) * 1000
        self.tick_current = 0.0

    def check_collision(self, point: tuple[float, float]) -> bool:
        if point[0] < self.x:
            return False
        if point[1] < self.y:
            return False
        if point[0] > self.x + self.width:
            return False
        if point[1] > self.y + self.height:
            return False
        return True

    def draw(self, surface):
        pygame.draw.rect(
            surface,
            self.color, (self.x, self.y, self.width, self.height)
        )
        surface.blit(self.text_obj, self.text_pos)

    def update(self, keys, mouse, dt):
        self.color = self.colors[0]
        if self.check_collision(mouse.get_pos()):
            self.color = self.colors[1]
            pressed = mouse.get_pressed()

            if any(pressed):
                self.color = self.colors[2]

                if self.long_press:
                    if not self.pressed_before:
                        self.action(self, pressed)
                    if self.tick_current >= self.tick_time:
                        self.tick_current %= self.tick_time
                        self.action(self, pressed)
                    self.tick_current += dt
            else:
                if not self.long_press:
                    if self.pressed_before:
                        self.action(self, self.pressed_before_buttons)

                self.tick_current = 0

            self.pressed_before = any(pressed)
            self.pressed_before_buttons = pressed


class BoardButtonManager:
    def __init__(self, game, board_size_px=200):
        self.boards = []
        self.board_size_px = board_size_px
        self.game = game
        self.load_boards()

    def load_board(self, board_name):
        import path
        with open(f'boards/{board_name}.pth', 'r') as board:
            content = board.readlines()
            size = int(content.pop(0))

            # generate tiles
            tile_size = self.board_size_px // size
            tiles = []
            for x in range(size):
                line = []
                for y in range(size):
                    tile = path.Tile(x * tile_size, y * tile_size, tile_size)
                    line.append(tile)
                tiles.append(line)

            # read tiles from file
            p = re.compile(r'Tile\((?P<x>[0-9]+), (?P<y>[0-9]+), (?P<tile_type>[A-Z]+)\)')
            for tile in content:
                m = p.match(tile)
                tiles[int(m.group('x'))][int(m.group('y'))].tile_type = m.group('tile_type')
        return size, tiles

    def load_boards(self):
        self.boards.clear()

        def load_board(button, pressed):
            self.game.load_board(button.filename)
            self.game.show_screen_index = 0

        # check for files
        files = []
        for file in os.listdir('boards'):
            name, extension = file.split('.')
            if extension == 'pth':
                files.append(name)
        default_index = files.index('default_board')
        if default_index != -1:
            files.insert(0, files.pop(default_index))

        for index, b in enumerate(files):
            size, tiles = self.load_board(b)
            self.boards.append(
                BoardPreview(
                    50 + (25 + self.board_size_px) * index, 50,
                    self.board_size_px,
                    b,
                    action=load_board,
                    elements=tiles
                )
            )

    def draw(self, surface):
        def perform_draw(item):
            if type(item) == list:
                for el in item:
                    perform_draw(el)
            else:
                item.draw(surface)

        for item in self.boards:
            perform_draw(item)

    def update(self, keys, mouse, dt):
        def perform_update(item):
            if type(item) == list:
                for el in item:
                    perform_update(el)
            else:
                item.update(keys, mouse, dt)

        for item in self.boards:
            perform_update(item)


class BoardPreview(Button):
    def __init__(self, x, y, size, filename, action, elements):
        super().__init__(x, y, width=size, height=size, text=filename, action=action, anchor_x='left', anchor_y='top',
                         font=pygame.font.SysFont('', 36))
        self.filename = filename
        self.cached_view = pygame.Surface((size, size))
        for line in elements:
            for el in line:
                el.draw(self.cached_view)

    def draw(self, surface):
        surface.blit(self.cached_view, (self.x, self.y))
        surface.blit(self.text_obj, self.text_pos)
