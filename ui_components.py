import pygame

from game_constants import ACCENT_BLUE, CARD_DISABLED, MUTED_COLOR, TEXT_COLOR


class Button:
    def __init__(self, rect: pygame.Rect, label: str):
        self.rect = rect
        self.label = label

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, enabled: bool) -> None:
        fill = ACCENT_BLUE if enabled else CARD_DISABLED
        pygame.draw.rect(screen, fill, self.rect, border_radius=14)
        pygame.draw.rect(screen, TEXT_COLOR, self.rect, width=2, border_radius=14)
        text = font.render(self.label, True, TEXT_COLOR if enabled else MUTED_COLOR)
        screen.blit(text, text.get_rect(center=self.rect.center))

    def contains(self, pos) -> bool:
        return self.rect.collidepoint(pos)
