# coding:utf-8
import os

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QKeySequence
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QShortcut
from qfluentwidgets import ScrollArea, InfoBar, RoundMenu, Action, FluentIcon, DropDownPushButton, StateToolTip, \
    ProgressBar, TextEdit, MessageBox, InfoBarPosition

from common.config import cfg
from common.style_sheet import StyleSheet
from common.update_checker import update_checker
from common.util import Lang, LangTranslatorThread, save_lang_file, FTBQuest
from components.file_browser import FileBrowser
from components.pivot_interface import PivotInterface
from .search_interface import SearchDictInterface


class WorkInterface(ScrollArea):
    """ Home interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ext = None
        self.first_update_flag = True
        self.data = [
            ['', '你可以在左侧工作区域内选择json格式的语言文件，双击读取并编辑', '', ''],
            ['', '需要注意的是你只能编辑译文', '', ''],
            ['', '点击保存进度按钮可以保留此次工作进度', '', '']
        ]
        self.stateTooltip = None
        self.translator_thread = None
        self.trans_list = None
        self.lang = Lang()
        self.quest = None

        self.view = QWidget(self)
        self.layout = QHBoxLayout(self.view)
        self.view.setObjectName('view')

        self.__initWidget()

    def __initWidget(self):
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.fileBrowser = FileBrowser(cfg.workFolder)
        self.searchDictInterface = SearchDictInterface()

        self.middleBox = QWidget()
        self.middleLayout = QVBoxLayout()

        self.langBrowser = PivotInterface(self.data)
        self.langBrowser.setMinimumHeight(620)

        self.progressBar = ProgressBar()
        self.progressBar.setValue(0)
        self.middleLayout.addWidget(self.progressBar)

        self.subHbox = QHBoxLayout()
        button_box = QWidget()
        button_box.setLayout(self.subHbox)

        self.menu_save = RoundMenu(parent=self)
        self.menu_trans = RoundMenu(parent=self)
        self.menu_extra = RoundMenu(parent=self)

        self.action_trans_start = Action(FluentIcon.SEND_FILL, '开始机翻')
        self.action_trans_start.setShortcut('F1')
        self.action_trans_stop = Action(FluentIcon.CLOSE, '终止机翻')
        self.action_trans_stop.setShortcut('F2')
        self.action_save_lang = Action(FluentIcon.SAVE, '保存')
        self.action_save_lang.setShortcut('F3')
        self.action_save_lang_as = Action(FluentIcon.SAVE_AS, '另存为')
        self.action_save_lang_as.setShortcut('F4')
        self.action_save_cache = Action(FluentIcon.PIN, '保存进度')
        self.action_save_cache.setShortcut('F5')
        self.action_migrate = Action(FluentIcon.HISTORY, '从旧版本迁移')

        shortcut1 = QShortcut(QKeySequence("F1"), self.view)
        shortcut2 = QShortcut(QKeySequence("F2"), self.view)
        shortcut3 = QShortcut(QKeySequence("F3"), self.view)
        shortcut4 = QShortcut(QKeySequence("F4"), self.view)
        shortcut5 = QShortcut(QKeySequence("F5"), self.view)
        shortcut1.activated.connect(self.handle_translate_start)
        shortcut2.activated.connect(self.handle_translate_stop)
        shortcut3.activated.connect(self.handle_save)
        shortcut4.activated.connect(self.handle_save_as)
        shortcut5.activated.connect(self.handle_save_cache)

        self.action_trans_start.triggered.connect(self.handle_translate_start)
        self.action_trans_start.triggered.connect(self.__checkUpdate)
        self.action_trans_stop.triggered.connect(self.handle_translate_stop)
        self.action_save_cache.triggered.connect(self.handle_save_cache)
        self.action_save_lang.triggered.connect(self.handle_save)
        self.action_save_lang_as.triggered.connect(self.handle_save_as)
        self.action_migrate.triggered.connect(self.handle_migrate)

        self.menu_trans.addAction(self.action_trans_start)
        self.menu_trans.addAction(self.action_trans_stop)
        self.menu_trans.addAction(self.action_migrate)
        self.menu_save.addAction(self.action_save_lang)
        self.menu_save.addAction(self.action_save_lang_as)
        self.menu_save.addAction(self.action_save_cache)

        self.dropDownPushButton_save = DropDownPushButton('保存', self, FluentIcon.SAVE)
        self.dropDownPushButton_trans = DropDownPushButton('预翻译', self, FluentIcon.BASKETBALL)
        self.dropDownPushButton_save.setMenu(self.menu_save)
        self.dropDownPushButton_trans.setMenu(self.menu_trans)
        self.subHbox.addWidget(self.dropDownPushButton_trans)
        self.subHbox.addWidget(self.dropDownPushButton_save)

        self.middleLayout.addWidget(self.langBrowser)
        self.middleLayout.addStretch(1)
        self.middleLayout.addWidget(button_box)
        self.middleBox.setLayout(self.middleLayout)

        self.searchBox = QWidget()
        self.searchLayout = QVBoxLayout()
        self.searchBox.setFixedWidth(300)
        self.transLog = TextEdit()
        self.transLog.setStyleSheet('background-color: transparent;border:none')
        self.transLog.setFixedSize(280, 320)
        self.transLog.setReadOnly(True)
        self.transLog.setPlainText(f'快捷键：\nCtrl+A-上一条\nCtrl+D-下一条\nCtrl+W上个文件\nCtrl+S下'
                                   f'个文件\nCtrl+Enter开始编辑\nEsc退出编辑\n\nCtrl+?搜索离线词典\n\nF1/F2-开始'
                                   f'/停止机翻\nF3/F4-保存/另存为')
        self.searchDictInterface.setFixedHeight(400)
        self.searchLayout.addWidget(self.searchDictInterface)
        # self.searchLayout.addWidget(self.searchCacheInterface)
        self.searchLayout.addStretch(1)
        self.searchLayout.addWidget(self.transLog)
        self.searchBox.setLayout(self.searchLayout)

        self.fileBrowser.chooseFile.connect(self.handle_choose_file)

        self.layout.addWidget(self.fileBrowser)
        self.layout.addWidget(self.middleBox)
        self.layout.addWidget(self.searchBox)

        self.fileBrowser.setObjectName('fileBrowser')
        self.transLog.setObjectName('transLog')
        StyleSheet.WORK_INTERFACE.apply(self)

    def __checkUpdate(self):
        if self.first_update_flag and update_checker.need_update and cfg.get(cfg.checkUpdateAtStartUp):
            self.first_update_flag = False
            title = self.tr('检测到新版本:%s' % update_checker.latest_version)
            content = self.tr('更新日志：%s\n' % update_checker.logs)
            w = MessageBox(title, content, self.window())
            if w.exec():
                QDesktopServices.openUrl(QUrl(update_checker.link))

    def update_trans_log(self, info):
        current_text = self.transLog.toHtml()
        new_text = current_text + "\n" + info
        self.transLog.setHtml(new_text)
        self.transLog.verticalScrollBar().setValue(
            self.transLog.verticalScrollBar().maximum()
        )

    def handle_choose_file(self, path):
        self.trans_list = None
        self.transLog.setPlainText('')
        ext = os.path.splitext(path)[1].lower()
        self.ext = ext
        try:
            if ext in ['.json', '.lang']:
                self.lang.read_lang(path, cache=True)
            elif ext == '.snbt':
                self.quest = FTBQuest(path)
                self.lang.set_lang(self.quest.lang)
            else:
                InfoBar.info(
                    self.tr('无法读取'),
                    self.tr('暂时只支持lang与snbt任务文件'),
                    duration=3000,
                    parent=self
                )
        except Exception as e:
            InfoBar.error(
                self.tr('错误'),
                self.tr(str(e)),
                duration=10000,
                parent=self
            )
        else:
            self.read_cache_tooltip()
            self.langBrowser.browseInterface.update_table(self.lang.lang_bilingual_list)
            self.langBrowser.reviewInterface.update_table(self.lang.lang_bilingual_list)
            self.langBrowser.reviewInterface.current_trans_info.setText('')
            if ext == '.json' or ext == '.lang':
                InfoBar.success(
                    self.tr('读取成功'),
                    self.tr('检测为%s语言文件' % ext),
                    duration=3000,
                    parent=self
                )
            elif ext == '.snbt':
                InfoBar.success(
                    self.tr('读取成功'),
                    self.tr('检测为snbt任务文件，已提取出需翻译部分'),
                    duration=3000,
                    parent=self
                )

    def read_cache_tooltip(self):
        if self.lang.cache_dic != {}:
            InfoBar.success(
                self.tr('读取到进度缓存'),
                self.tr(''),
                duration=5000,
                parent=self
            )

    def handle_translate_start(self):
        keepOriginal = cfg.get(cfg.keepOriginal)
        # if not cfg.get(cfg.keepOriginal):
        #     if not activate.activate:
        #         keepOriginal = False
        #         InfoBar.warning(
        #             title=self.tr('你的配置貌似有些问题'),
        #             content=self.tr("不用担心，我会已经帮你修正了😊"),
        #             orient=Qt.Horizontal,
        #             isClosable=False,  # disable close button
        #             position=InfoBarPosition.TOP_LEFT,
        #             duration=2000,
        #             parent=self
        #         )
        #     cfg.set(cfg.keepOriginal, True)

        self.translator_thread = LangTranslatorThread(self.lang.lang_bilingual_list, 'en', 'zh', cfg.get(cfg.appKey),
                                                      cfg.get(cfg.appSecret), keepOriginal)
        self.trans_list = self.lang.lang_bilingual_list
        self.translator_thread.finished.connect(self.on_translation_finished)
        self.translator_thread.progress.connect(self.progressBar.setValue)
        self.translator_thread.index.connect(self.langBrowser.reviewInterface.current_trans_info.setText)
        self.translator_thread.error.connect(self.on_translation_failed)
        self.translator_thread.info.connect(self.update_trans_log)
        self.translator_thread.start()

        self.progressBar.show()
        self.stateTooltip = StateToolTip(
            self.tr('翻译'), self.tr('执行中,请耐心等待'), self.window())
        self.stateTooltip.move(self.stateTooltip.getSuitablePos())
        self.stateTooltip.show()

    def handle_translate_stop(self):
        try:
            self.translator_thread.stop()
        except Exception as e:
            InfoBar.warning(
                self.tr('终止出错'),
                self.tr('错误信息:%s' % str(e)),
                duration=10000,
                parent=self
            )

    def on_translation_finished(self):
        self.progressBar.hide()
        self.stateTooltip.setContent(
            self.tr('完成，你可以在编辑视图中查看!') + ' 😆')
        self.stateTooltip.setState(True)
        self.stateTooltip = None
        self.langBrowser.browseInterface.update_table(self.lang.lang_bilingual_list)
        self.langBrowser.reviewInterface.update_table(self.lang.lang_bilingual_list)

    def on_translation_failed(self, error_msg):
        # 隐藏进度条，恢复用户界面
        self.progressBar.hide()
        # 弹出错误提示框
        InfoBar.error(
            self.tr('API调用失败'),
            self.tr('错误信息:%s' % error_msg),
            duration=10000,
            parent=self
        )
        self.progressBar.hide()
        self.stateTooltip.setState(True)
        self.stateTooltip = None

    def handle_save_cache(self):
        try:
            result = self.lang.save_cache()
        except Exception as e:
            InfoBar.error(
                self.tr('进度缓存失败'),
                self.tr('错误::%s' % str(e)),
                duration=10000,
                parent=self
            )
        else:
            InfoBar.success(
                self.tr('进度缓存成功'),
                self.tr('已保存于:%s' % result),
                duration=10000,
                parent=self
            )

    def handle_save_as(self):
        if self.ext == '.snbt':
            prefix_path = os.path.dirname(self.quest.input_path) + '/回填后文件'
            os.makedirs(prefix_path) if not os.path.exists(prefix_path) else None
            folder, _ = QFileDialog.getSaveFileName(self, "保存文件", prefix_path + '/' + self.quest.prefix
                                                    , "SNBT 文件 (*.snbt);;所有文件 (*)")
        else:
            original_path = os.path.dirname(self.lang.file_path) + '/zh_cn' if 'en' in self.lang.file_path else '/zh_CN'
            file_type = 'JSON 文件 (*.json);;' if 'json' in self.lang.file_path else 'LANG 文件 (*.lang);;'
            folder, _ = QFileDialog.getSaveFileName(self, "保存文件", original_path, f"{file_type}所有文件 (*)")

    def handle_save(self):
        if self.ext == '.snbt':
            prefix_path = os.path.dirname(self.quest.input_path) + '/回填后文件'
            os.makedirs(prefix_path) if not os.path.exists(prefix_path) else None
            folder = f"{prefix_path}/{self.quest.prefix}.snbt"
        else:
            folder = self.lang.file_path.replace('en_us.', 'zh_cn.')
            folder = folder.replace('en_US.', 'zh_CN.')
        self.save_lang_file(folder)

    def save_lang_file(self, path: str):
        if path:
            try:
                data = {row[0]: row[2] for row in self.lang.lang_bilingual_list if row[2] != ''}
                if self.ext != '.snbt':
                    save_lang_file(data, path)
                else:
                    save_lang_file(data, path, self.quest.backFill(data))
            except Exception as e:
                InfoBar.error(
                    self.tr('保存失败'),
                    self.tr('错误:%s' % str(e)),
                    duration=10000,
                    parent=self
                )
            else:
                InfoBar.success(
                    self.tr('保存成功'),
                    self.tr('已保存于:%s' % path),
                    duration=10000,
                    parent=self
                )

    def handle_migrate(self):
        title = self.tr('须知')
        content = self.tr(
            "此功能针对专业译者提供，主要从旧版本语言文件中迁移汉化\n"
            "使用时请提前在当前视图所打开的文件同级目录下创建old文件夹"
            "并将旧汉化的en_us和zh_cn放到此目录下")
        w = MessageBox(title, content, self.window())
        if not w.exec():
            return
        count = 0
        try:
            old_lang_root = os.path.dirname(self.lang.file_path) + '/old'
            if os.path.exists(old_lang_root):
                old_lang_en = None
                old_lang_zh = None
                for root, dirs, files in os.walk(old_lang_root):
                    for file in files:
                        file_low = file.lower()
                        if "zh_cn" in file_low:
                            old_lang_zh = Lang()
                            old_lang_zh.read_lang(os.path.join(root, file))
                        elif "en_us" in file_low:
                            old_lang_en = Lang()
                            old_lang_en.read_lang(os.path.join(root, file))
                if old_lang_zh and old_lang_en:
                    old_lang_zh_dic = old_lang_zh.lang_dic
                    old_lang_en_dic = old_lang_en.lang_dic
                    for i in range(0, len(self.lang.lang_bilingual_list)):
                        new_lang_en_text = self.lang.lang_bilingual_list[i][1]
                        for key, value in old_lang_en_dic.items():
                            if value == new_lang_en_text:
                                self.lang.lang_bilingual_list[i][2] = old_lang_zh_dic.get(key)
                                count = count + 1
                                break
                    self.langBrowser.browseInterface.update_table(self.lang.lang_bilingual_list)
                    self.langBrowser.reviewInterface.update_table(self.lang.lang_bilingual_list)
            else:
                raise Exception('缺少旧版本语言文件')
        except Exception as e:
            InfoBar.error(
                self.tr('迁移失败'),
                self.tr('错误:%s' % str(e)),
                duration=10000,
                parent=self
            )
        else:
            InfoBar.success(
                self.tr('迁移成功'),
                self.tr('导入了%s条' % str(count)),
                duration=3000,
                parent=self
            )
