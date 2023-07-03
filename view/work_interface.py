# coding:utf-8
import os

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import ScrollArea, InfoBar, RoundMenu, Action, FluentIcon, DropDownPushButton, StateToolTip, \
    ProgressBar, TextEdit, MessageBox, InfoBarPosition

from common.activate import activate
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
        self.action_trans_stop = Action(FluentIcon.CLOSE, '终止机翻')
        self.action_save_cache = Action(FluentIcon.PIN, '保存进度')
        self.action_save_lang = Action(FluentIcon.SAVE, '保存')
        self.action_migrate = Action(FluentIcon.HISTORY, '从旧版本迁移')

        self.action_trans_start.triggered.connect(self.handle_translate_start)
        self.action_trans_start.triggered.connect(self.__checkUpdate)
        self.action_trans_stop.triggered.connect(self.handle_translate_stop)
        self.action_save_cache.triggered.connect(self.handle_save_cache)
        self.action_save_lang.triggered.connect(self.handle_save_lang)
        self.action_migrate.triggered.connect(self.handle_migrate)

        self.menu_trans.addAction(self.action_trans_start)
        self.menu_trans.addAction(self.action_trans_stop)
        self.menu_trans.addAction(self.action_migrate)
        self.menu_save.addAction(self.action_save_cache)
        self.menu_save.addAction(self.action_save_lang)

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
        if update_checker.need_update and cfg.get(cfg.checkUpdateAtStartUp):
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
        if not cfg.get(cfg.keepOriginal):
            if not activate.activate:
                keepOriginal = False
                InfoBar.warning(
                    title=self.tr('你的配置貌似有些问题'),
                    content=self.tr("不用担心，我会已经帮你修正了😊"),
                    orient=Qt.Horizontal,
                    isClosable=False,  # disable close button
                    position=InfoBarPosition.TOP_LEFT,
                    duration=2000,
                    parent=self
                )
            cfg.set(cfg.keepOriginal, True)

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

    def handle_save_lang(self):
        if self.ext == '.snbt':
            prefix_path = os.path.dirname(self.quest.input_path) + '/回填后文件'
            os.makedirs(prefix_path) if not os.path.exists(prefix_path) else None
            folder, _ = QFileDialog.getSaveFileName(self, "保存文件", prefix_path + '/' + self.quest.prefix
                                                    , "SNBT 文件 (*.snbt);;所有文件 (*)")
        else:
            folder, _ = QFileDialog.getSaveFileName(self, "保存文件", os.path.dirname(self.lang.file_path) + '/zh_cn'
                                                    , "JSON 文件 (*.json);;LANG 文件 (*.lang);;所有文件 (*)")
        if folder:
            try:
                data = {row[0]: row[2] for row in self.lang.lang_bilingual_list if row[2] != ''}
                if self.ext != '.snbt':
                    save_lang_file(data, folder)
                else:
                    save_lang_file(data, folder, self.quest.backFill(data))
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
                    self.tr('已保存于:%s' % folder),
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
