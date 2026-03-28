import pygame

from game_constants import ACCENT_BLUE, CARD_DISABLED, MUTED_COLOR, TEXT_COLOR


class Button:
    def __init__(self, rect: pygame.Rect, label: str):
        self.rect = rect
        self.label = label

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, enabled: bool) -> None:
        outer = self.rect.inflate(0, 4)
        shadow = pygame.Surface((outer.width, outer.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 8, 24, 130), shadow.get_rect(), border_radius=16)
        screen.blit(shadow, outer.topleft)

        fill = (10, 40, 96) if enabled else CARD_DISABLED
        pygame.draw.rect(screen, fill, self.rect, border_radius=14)
        pygame.draw.rect(screen, ACCENT_BLUE if enabled else MUTED_COLOR, self.rect, width=2, border_radius=14)

        top_strip = pygame.Rect(self.rect.x + 6, self.rect.y + 6, self.rect.width - 12, 8)
        pygame.draw.rect(
            screen,
            (108, 236, 255) if enabled else MUTED_COLOR,
            top_strip,
            border_radius=4,
        )
        text = font.render(self.label, True, TEXT_COLOR if enabled else MUTED_COLOR)
        screen.blit(text, text.get_rect(center=self.rect.center))

    def contains(self, pos) -> bool:
        return self.rect.collidepoint(pos)
