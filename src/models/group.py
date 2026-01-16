"""
Group data model.
"""

from dataclasses import dataclass
from typing import Optional

from ..config.constants import GROUP_COLORS, GROUP_COLOR_NAMES, EMOJI_TO_COLOR_NAME


@dataclass
class Group:
    """
    Represents a custom group for organizing accounts.

    Attributes:
        name: The group name.
        color: Color name (from GROUP_COLOR_NAMES) or hex color code.
    """
    name: str
    color: str = "red"

    def __post_init__(self):
        """Validate and migrate color value."""
        # Migrate emoji colors to color names
        if self.color in EMOJI_TO_COLOR_NAME:
            self.color = EMOJI_TO_COLOR_NAME[self.color]
        # Validate color - default to red if unknown and not a hex color
        elif self.color not in GROUP_COLOR_NAMES and not self.color.startswith('#'):
            self.color = "red"

    @property
    def color_hex(self) -> str:
        """Get the hex color code for this group."""
        if self.color.startswith('#'):
            return self.color
        return GROUP_COLORS.get(self.color, '#808080')

    def to_dict(self) -> dict:
        """Convert group to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'color': self.color,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Group':
        """Create a Group from a dictionary."""
        return cls(
            name=data.get('name', ''),
            color=data.get('color', 'red'),
        )

    def __eq__(self, other: object) -> bool:
        """Two groups are equal if they have the same name."""
        if not isinstance(other, Group):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        """Hash based on name."""
        return hash(self.name)
