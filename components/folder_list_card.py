from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
from qfluentwidgets import Dialog, ExpandSettingCard
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets.components.settings.folder_list_setting_card import FolderItem


class FolderListCard(ExpandSettingCard):
    def __init__(self, title: str, content: str = None, directory="./", folders=None, parent=None):
        super().__init__(FIF.FOLDER, title, content, parent)
        if folders is None:
            folders = []
        self._dialogDirectory = directory
        self.folders = folders
        self.__initWidget()

    def __initWidget(self):
        self.addWidget(QWidget())
        self.viewLayout.setSpacing(0)
        self.viewLayout.setAlignment(Qt.AlignTop)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        for folder in self.folders:
            self.__add_folder_item(folder)

    def update_folder(self, folders):
        self.__remove_all_folder_widget()
        self.folders = folders
        for folder in folders:
            self.__add_folder_item(folder)
        self._adjustViewSize()

    def __add_folder_item(self, folder: str):
        item = FolderItem(folder, self.view)
        item.removed.connect(self.__show_confirm_dialog)
        self.viewLayout.addWidget(item)
        self._adjustViewSize()

    def __show_confirm_dialog(self, item: FolderItem):
        name = Path(item.folder).name
        title = self.tr('确认删除此文件？')
        content = self.tr("提取本地键将不考虑 ") + f'"{name}"' + \
                  self.tr(",此操作不删除本地文件")
        w = Dialog(title, content, self.window())
        w.yesSignal.connect(lambda: self.__remove_folder(item))
        w.exec_()

    def __remove_folder(self, item: FolderItem):
        if item.folder not in self.folders:
            return
        self.folders.remove(item.folder)
        self.viewLayout.removeWidget(item)
        self._adjustViewSize()

    def __remove_all_folder_widget(self):
        self.folders = []
        while self.viewLayout.count():
            item = self.viewLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                self.viewLayout.removeWidget(widget)
        self._adjustViewSize()
