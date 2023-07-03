# coding:utf-8
import json
import os.path

from PyQt5.QtCore import Qt, pyqtSignal, QFile
from PyQt5.QtWidgets import QVBoxLayout, QFileSystemModel, QLabel, QFileDialog, \
    QItemDelegate, QCheckBox, QScrollArea, QInputDialog
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import TreeView, Action, RoundMenu, MessageBox, LineEdit, InfoBar, \
    InfoBarPosition

from common.config import cfg
from common.style_sheet import StyleSheet


class CheckBoxDelegate(QItemDelegate):
    def createEditor(self, parent, option, index):
        checkbox = QCheckBox(parent)
        checkbox.setStyleSheet("margin-left: 5px")  # 调整复选框的样式和位置
        return checkbox

    def setEditorData(self, editor, index):
        value = index.data(Qt.CheckStateRole)
        if value == Qt.Checked:
            editor.setChecked(True)
        else:
            editor.setChecked(False)

    def setModelData(self, editor, model, index):
        value = Qt.Checked if editor.isChecked() else Qt.Unchecked
        model.setData(index, value, Qt.CheckStateRole)


class FileBrowser(QScrollArea):
    chooseFile = pyqtSignal(str)

    def __init__(self, configItem, parent=None):
        super().__init__(parent=parent)
        folder = cfg.get(configItem)
        self.configItem = configItem
        self.setFixedWidth(256)
        # 垂直布局
        self.v_box_layout = QVBoxLayout(self)
        # 控件
        self.label1 = QLabel('当前目录(点击下方地址切换)', self)
        self.label2 = QLabel(folder, self)
        self.label2.setWordWrap(True)
        self.label2.mousePressEvent = self.onLabel2Clicked
        self.model = QFileSystemModel()
        self.model.setRootPath(folder)
        # 过滤
        # self.model.setNameFilters(['*.snbt', '*.json', ])
        self.model.setNameFilterDisables(False)
        # 展示
        self.tree_view = TreeView(self)
        self.tree_view.setModel(self.model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.hideColumn(1)
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3)
        self.tree_view.setRootIndex(self.model.index(folder))

        self.v_box_layout.addWidget(self.label1)
        self.v_box_layout.addWidget(self.label2)
        self.v_box_layout.addWidget(self.tree_view)
        # 设置 CheckboxDelegate 为 delegate
        # delegate = CheckBoxDelegate()
        # self.tree_view.setItemDelegate(delegate)

        # 添加右键菜单
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)

        # 创建右键菜单
        self.context_menu = RoundMenu(parent=self)
        self.rename_action = Action(FIF.SYNC, "重命名", self)
        self.create_folder_action = Action(FIF.ADD, "新建文件夹", self)
        self.delete_action = Action(FIF.CLOSE, "删除", self)
        self.submenu = RoundMenu("额外工具", self)
        self.submenu.setIcon(FIF.BOOK_SHELF)
        self.json_to_lang_action = Action(FIF.CARE_DOWN_SOLID, "JSON转LANG", self)
        self.lang_to_json_action = Action(FIF.CARE_UP_SOLID, "LANG转JSON", self)
        self.context_menu.addAction(self.rename_action)
        self.context_menu.addAction(self.create_folder_action)
        self.context_menu.addAction(self.delete_action)
        self.submenu.addActions([
            self.json_to_lang_action,
            self.lang_to_json_action,
        ])
        self.context_menu.addMenu(self.submenu)
        # 连接信号与槽函数
        self.rename_action.triggered.connect(self.rename_file)
        self.create_folder_action.triggered.connect(self.create_folder)
        self.json_to_lang_action.triggered.connect(self.json_to_lang)
        self.lang_to_json_action.triggered.connect(self.lang_to_json)
        self.delete_action.triggered.connect(self.delete_file)
        self.tree_view.doubleClicked.connect(self.tree_clicked)
        # 应用qss
        self.tree_view.setObjectName('treeView')
        self.label1.setObjectName('label1')
        self.label2.setObjectName('label2')
        StyleSheet.FILE_BROWSER.apply(self)

    def show_context_menu(self, point):
        index = self.tree_view.indexAt(point)
        if index.isValid():
            self.context_menu.exec_(self.tree_view.viewport().mapToGlobal(point))

    def rename_file(self):
        index = self.tree_view.currentIndex()
        if index.isValid():
            old_path = self.model.filePath(index)
            new_name, ok = QInputDialog.getText(self, "重命名", "请输入新的文件名：",
                                                LineEdit.Normal, self.model.fileName(index))
            if ok and new_name:
                new_path = self.model.filePath(index.parent()) + "/" + new_name
                file = QFile(old_path)
                if file.rename(new_path):
                    InfoBar.success(
                        title=self.tr('成功'),
                        content=self.tr("文件重命名成功！"),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=1500,
                        parent=self.parent()
                    )
                else:
                    InfoBar.warning(
                        title=self.tr('错误'),
                        content=self.tr("文件重命名失败！"),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=1500,
                        parent=self.parent()
                    )

    def create_folder(self):
        index = self.tree_view.currentIndex()
        if index.isValid():
            path = self.model.filePath(index)
            new_folder_name, ok = QInputDialog.getText(self, "新建文件夹", "请输入文件夹名称：",
                                                       LineEdit.Normal, "New Folder")
            if ok and new_folder_name:
                new_folder_path = path + "/" + new_folder_name
                if self.model.mkdir(index, new_folder_path):
                    InfoBar.success(
                        title=self.tr('成功'),
                        content=self.tr("文件夹创建成功！"),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=1500,
                        parent=self.parent()
                    )
                else:
                    InfoBar.warning(
                        title=self.tr('错误'),
                        content=self.tr("文件创建失败！"),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=1500,
                        parent=self.parent()
                    )

    def delete_file(self):
        index = self.tree_view.currentIndex()
        if index.isValid():
            title = self.tr('确认删除？')
            content = self.tr(
                "你会永远失去它")
            w = MessageBox(title, content, self.window())
            if w.exec():
                if self.model.remove(index):
                    InfoBar.success(
                        title=self.tr('成功'),
                        content=self.tr("删除成功！"),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=1500,
                        parent=self.parent()
                    )
                else:
                    InfoBar.warning(
                        title=self.tr('错误'),
                        content=self.tr("文件删除失败！"),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.BOTTOM_RIGHT,
                        duration=1500,
                        parent=self
                    )
            else:
                return

    def lang_to_json(self):
        index = self.tree_view.currentIndex()
        if index.isValid():
            try:
                path = self.model.filePath(index)
                if path.endswith('.lang'):
                    with open(path, 'r', encoding='utf-8') as f:
                        lang_data = f.read()
                        # 清理注释
                        lang_data = '\n'.join(
                            line for line in lang_data.split('\n') if not line.strip().startswith("#"))
                        # 分割键值对
                        lang_data = [line.strip() for line in lang_data.split('\n') if line.strip()]
                        lang_dict = {}
                        for line in lang_data:
                            key, value = line.split("=", maxsplit=1)
                            lang_dict[key.strip()] = value.strip()

                    # 保存到原先目录下
                    file_dir = os.path.dirname(path)
                    file_name = os.path.splitext(os.path.basename(path))[0]
                    json_file_path = os.path.join(file_dir, file_name + '.json')

                    with open(json_file_path, 'w', encoding='utf-8') as f:
                        json.dump(lang_dict, f, ensure_ascii=False, indent=4)
            except Exception as e:
                InfoBar.error(
                    title=self.tr('错误'),
                    content=self.tr(str(e)),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=1500,
                    parent=self
                )
            else:
                InfoBar.success(
                    title=self.tr('成功'),
                    content=self.tr("转化成功！"),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=1500,
                    parent=self.parent()
                )

    def json_to_lang(self):
        index = self.tree_view.currentIndex()
        if index.isValid():
            try:
                path = self.model.filePath(index)
                if path.endswith('.json'):
                    with open(path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)

                    # 保存到原先目录下
                    file_dir = os.path.dirname(path)
                    file_name = os.path.splitext(os.path.basename(path))[0]
                    json_file_path = os.path.join(file_dir, file_name + '.lang')

                    with open(json_file_path, 'w', encoding='utf-8') as f:
                        for key, value in json_data.items():
                            value = json.dumps(value, ensure_ascii=False)
                            f.write(f'{key}={value}\n')
            except Exception as e:
                InfoBar.error(
                    title=self.tr('错误'),
                    content=self.tr(str(e)),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=1500,
                    parent=self
                )
            else:
                InfoBar.success(
                    title=self.tr('成功'),
                    content=self.tr("转化成功！"),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.BOTTOM_RIGHT,
                    duration=1500,
                    parent=self.parent()
                )

    def onLabel2Clicked(self, t):
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("请选择目录"), "./")
        if not folder or cfg.get(self.configItem) == folder:
            return
        cfg.set(self.configItem, folder)
        self.freshFileBrowser()

    def freshFileBrowser(self):
        folder = cfg.get(self.configItem)
        self.label2.setText(folder)
        self.model.setRootPath(folder)
        self.tree_view.setRootIndex(self.model.index(folder))

    def tree_clicked(self, Qmodelidx):
        file_path = self.model.filePath(Qmodelidx)
        if os.path.isfile(file_path):
            self.chooseFile.emit(file_path)
        # print(self.model.fileName(Qmodelidx))
        # print(self.model.fileInfo(Qmodelidx))
