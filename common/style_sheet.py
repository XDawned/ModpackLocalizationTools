# coding: utf-8
from enum import Enum

from qfluentwidgets import StyleSheetBase, Theme, qconfig


class StyleSheet(StyleSheetBase, Enum):
    """ Style sheet  """

    LINK_CARD = "link_card"
    FILE_BROWSER = "file_browser"
    MAIN_WINDOW = "main_window"
    SAMPLE_CARD = "sample_card"
    HOME_INTERFACE = "home_interface"
    WORK_INTERFACE = "work_interface"
    ICON_INTERFACE = "icon_interface"
    VIEW_INTERFACE = "view_interface"
    SETTING_INTERFACE = "setting_interface"
    NAVIGATION_VIEW_INTERFACE = "navigation_view_interface"
    TEST = "test"

    def path(self, theme=Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme
        return f":/qss/{theme.value.lower()}/{self.value}.qss"
