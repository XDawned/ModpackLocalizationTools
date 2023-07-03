# coding:utf-8
import json
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QFileDialog
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import InfoBar
from qfluentwidgets import (SettingCardGroup, PushSettingCard, ScrollArea, ExpandLayout,
                            PrimaryPushSettingCard, MessageBox, StateToolTip, SwitchSettingCard, setTheme, )

from common.config import cfg
from common.style_sheet import StyleSheet
from common.util import get_if_folder_exists, Mod, ResourcePack, get_if_subfolder_exists, save_file, FTBQuest, \
    check_file_exists, BetterQuest
from components.folder_list_card import FolderListCard


class ModpackExtractInterface(ScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.packFolder = ''
        self.un_trans_mod_list = []
        self.ftbq_list = []
        self.bq_list = []
        self.scrollWidget = QWidget()
        self.stateTooltip = None
        self.processThread = None
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # setting label
        self.packLabel = QLabel(self.tr("整合包待翻部分提取"), self)

        self.packFolderCard = PushSettingCard(
            self.tr('选择目录'),
            FIF.BOOK_SHELF,
            self.tr("整合包版本目录（.minecraft或版本目录，需包含mods、config等）"),
            cfg.get(cfg.workFolder),
            self.scrollWidget
        )
        self.extractFileGroup = SettingCardGroup(
            self.tr("检测到的待提文件"), self.scrollWidget)

        self.modFolderCard = FolderListCard(
            self.tr('Mods(可匹配已有汉化资源包)'),
            self.tr(
                "检测到以下未汉化的模组文件，如果存在i18n模组请将其生成的汉化资源包放到resourcepack目录下,默认i18n资源包位于C:/Users/用户名/.i18nupdatemod下"),
            directory='./',
            parent=self.extractFileGroup
        )
        self.ftbqFolderCard = FolderListCard(
            self.tr('FTBQuests'),
            self.tr(
                "检测到以下FTBQuests任务文件,使用前请确保任务没有使用键值，如果已使用键值可以将lang手动导入工作目录中"),
            directory='./',
            parent=self.extractFileGroup
        )
        self.bqFolderCard = FolderListCard(
            self.tr('BetterQuesting'),
            self.tr("检测到以下BetterQuesting任务文件"),
            directory='./',
            parent=self.extractFileGroup
        )
        self.configGroup = SettingCardGroup(
            self.tr("配置"), self.scrollWidget)
        self.lowVersionLangFormatCard = SwitchSettingCard(
            FIF.DATE_TIME,
            self.tr('是否保留为.lang类型语言文件'),
            self.tr('如果整合包版本为1.13及以下请开启此选项'),
            configItem=cfg.lowVersionLangFormat,
            parent=self.configGroup
        )
        self.funcGroup = SettingCardGroup(
            self.tr("执行操作"), self.scrollWidget)
        self.buttonBoxCard = PrimaryPushSettingCard(
            self.tr('提取'),
            FIF.FEEDBACK,
            self.tr('开始提取'),
            self.tr('从上述内容提取lang文件'),
            parent=self.funcGroup
        )
        self.buttonBoxCard.clicked.connect(self.generate_lang)
        self.__initWidget()

    def __initWidget(self):
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        # initialize style sheet
        self.scrollWidget.setObjectName('scrollWidget')
        self.packLabel.setObjectName('packLabel')
        StyleSheet.SETTING_INTERFACE.apply(self)

        # initialize layout
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.packLabel.move(36, 30)
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.extractFileGroup.addSettingCard(self.modFolderCard)
        self.extractFileGroup.addSettingCard(self.ftbqFolderCard)
        self.extractFileGroup.addSettingCard(self.bqFolderCard)
        self.configGroup.addSettingCard(self.lowVersionLangFormatCard)
        self.funcGroup.addSettingCard(self.buttonBoxCard)
        self.expandLayout.addWidget(self.packFolderCard)
        self.expandLayout.addWidget(self.extractFileGroup)
        self.expandLayout.addWidget(self.configGroup)
        self.expandLayout.addWidget(self.funcGroup)

    def __connectSignalToSlot(self):
        cfg.appRestartSig.connect(self.__showRestartTooltip)
        cfg.themeChanged.connect(setTheme)
        self.packFolderCard.clicked.connect(self.__onPackFolderCardClicked)
        self.lowVersionLangFormatCard.checkedChanged.connect(
            self.__showRestartTooltip)

    def __showRestartTooltip(self):
        InfoBar.success(
            self.tr('更新成功'),
            self.tr('如未生效请尝试重启软件'),
            duration=1500,
            parent=self
        )

    def __onPackFolderCardClicked(self):
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("请选择整合包目录"), "./")
        if not folder:
            return
        self.packFolderCard.setContent(folder)
        self.packFolder = folder
        self.check_modpack()

    def check_modpack(self):
        self.stateTooltip = StateToolTip(
            self.tr('初始化中'), self.tr('请耐心等待'), self.window())
        self.stateTooltip.move(self.stateTooltip.getSuitablePos())
        self.stateTooltip.show()
        self.checkThread = CheckThread(self.packFolder)
        self.checkThread.finished.connect(self.on_finished)
        self.checkThread.finished.connect(self.update_card)
        self.checkThread.error.connect(self.on_failed)
        self.checkThread.start()

    def update_card(self, check):
        self.un_trans_mod_list = self.checkThread.un_trans_mod_list
        self.ftbq_list = self.checkThread.ftbq_list
        self.bq_list = self.checkThread.bq_list
        self.modFolderCard.updateFolder(mod.path for mod in self.un_trans_mod_list)
        self.ftbqFolderCard.updateFolder(self.ftbq_list)
        self.bqFolderCard.updateFolder(self.bq_list)

    def generate_lang(self):
        title = self.tr('注意混淆')
        content = self.tr(
            "此操作将会把语言文件提取到工作目录中，请尽量确保工作目录下为空，否则可能会因混淆而产生其它问题！！！")
        w = MessageBox(title, content, self.window())
        if not w.exec():
            return
        self.stateTooltip = StateToolTip(
            self.tr('提取中'), self.tr('请耐心等待'), self.window())
        self.stateTooltip.move(self.stateTooltip.getSuitablePos())
        self.stateTooltip.show()
        self.processThread = ProcessThread(self.un_trans_mod_list, self.ftbq_list, self.bq_list)
        self.processThread.finished.connect(self.on_finished)
        # self.processThread.progress.connect(self.progressBar.setValue)
        self.processThread.error.connect(self.on_failed)
        self.processThread.start()

    def on_finished(self, text: str):
        # self.progressBar.hide()
        self.stateTooltip.setContent(
            text)
        self.stateTooltip.setState(True)
        self.stateTooltip = None

    def on_failed(self, error_msg):
        InfoBar.error(
            self.tr('提取失败'),
            self.tr(error_msg),
            duration=10000,
            parent=self
        )


class CheckThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    un_trans_mod_list = []
    ftbq_list = []
    bq_list = []

    def __init__(self, pack_folder):
        super().__init__()
        self.packFolder = pack_folder

    def run(self):
        try:
            mods_folder_path = get_if_folder_exists(self.packFolder, 'mods')
            resource_pack_folder_path = get_if_folder_exists(self.packFolder, 'resourcepacks')
            ftbq_folder_path = get_if_subfolder_exists(self.packFolder, 'config/ftbquests')
            bq_folder_path = get_if_subfolder_exists(self.packFolder, 'config/betterquesting')
            i18n_trans_mod_list = []
            if resource_pack_folder_path:
                resource_pack_paths = (str(path) for path in Path(resource_pack_folder_path).rglob("*.zip"))
                for resource_pack_path in resource_pack_paths:
                    resource_pack = ResourcePack(resource_pack_path)
                    i18n_trans_mod_list.extend(resource_pack.mods)
            if mods_folder_path:
                mod_paths = [str(path) for path in Path(mods_folder_path).rglob("*.jar")]
                for mod_path in mod_paths:
                    mod = Mod(mod_path)
                    if mod.modName not in i18n_trans_mod_list and len(mod.langList) > 0:  # 排除i18n汉化及无本地化模组
                        # 检查官译
                        flag = False
                        for lang in mod.langList:  # 防止语言文件名称大小写及类型不统一
                            if 'zh_cn' in lang.lower():
                                flag = True
                                break
                        if not flag:
                            lang_text = mod.get_lang_text(mod.langList[0])
                            if len(lang_text) > 5:  # 忽略空或过小语言文件
                                self.un_trans_mod_list.append(mod)

            if ftbq_folder_path:
                self.ftbq_list = [str(path) for path in Path(ftbq_folder_path).rglob("*.snbt")]
            if bq_folder_path:
                self.bq_list = [check_file_exists(bq_folder_path, "DefaultQuests.json")]
        except Exception as e:
            self.error.emit(str(e))
        else:
            self.finished.emit(self.tr('初始化完成'))


class ProcessThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, un_trans_mod_list, ftbq_list, bq_list):
        super().__init__()
        self.work_folder = cfg.get(cfg.workFolder)
        self.un_trans_mod_list = un_trans_mod_list
        self.ftbq_list = ftbq_list
        self.bq_list = bq_list

    def run(self):
        try:
            for mod in self.un_trans_mod_list:
                if mod.langList:
                    lang_path = self.work_folder + '/mods/' + mod.modName + '/lang/' + mod.langList[0]
                    lang_name = mod.langList[0]
                    for lang in mod.langList:
                        if 'en_us' in lang.lower():
                            lang_path = self.work_folder + '/mods/' + mod.modName + '/lang/' + lang
                            lang_name = lang
                            break
                    save_file(mod.get_lang_text(lang_name), lang_path)

            ftbq_lang = {}
            if len(self.ftbq_list) > 0:
                for ftbq in self.ftbq_list:
                    quest = FTBQuest(ftbq)
                    if 'reward_tables' in str(quest.input_path):  # 奖励表不处理
                        continue
                    if quest.prefix in ['data', 'chapter_groups']:
                        quest_local_path = self.work_folder + '/ftbquests/local/' + quest.prefix + '.snbt'
                    else:
                        quest_local_path = self.work_folder + '/ftbquests/local/chapters/' + quest.prefix + '.snbt'
                    save_file(quest.dumps(quest.quest_local), quest_local_path)
                    ftbq_lang.update(quest.lang)
                quest_lang_path = self.work_folder + '/ftbquests/lang/en_us.json'
                save_file(json.dumps(ftbq_lang, indent=1, ensure_ascii=False), quest_lang_path)

            bq_lang = {}
            if len(self.bq_list) > 0:
                for bq in self.bq_list:
                    quest = BetterQuest(bq)
                    quest_local_path = self.work_folder + '/betterquesting/local/DefaultQuests.json'
                    save_file(quest.dumps(quest.quest_local), quest_local_path)
                    bq_lang.update(quest.lang)
                quest_lang_path = self.work_folder + '/betterquesting/lang/en_us.json'
                save_file(json.dumps(bq_lang, indent=1, ensure_ascii=False), quest_lang_path)
        except Exception as e:
            self.error.emit(str(e))
        else:
            self.finished.emit(self.tr('完成，你可以在主工作台中查看!') + ' 😆')
