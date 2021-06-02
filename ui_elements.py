import pygame


class Label:
    def __init__(self, x, y, text, width=0, height=0, **kwargs):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        import path
        self.font = kwargs.get('font', path.FONT)
        self.font_color = kwargs.get('font_color', path.FONT_COLOR)

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
            x += width

        if anchor_y == 'top':
            pass
        elif anchor_y == 'center':
            y += height // 2
        elif anchor_y == 'bottom':
            y -= height

        super().__init__(x, y, text, width, height, **kwargs)
        self.colors = colors
        self.color = self.colors[0]
        self.action = action
        self.pressed_before = False

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

    def update(self, keys, mouse):
        self.color = self.colors[0]
        if self.check_collision(mouse.get_pos()):
            self.color = self.colors[1]
            if mouse.get_pressed()[0]:
                self.color = self.colors[2]
                if not self.pressed_before:
                    self.action(self)
            self.pressed_before = mouse.get_pressed()[0]
