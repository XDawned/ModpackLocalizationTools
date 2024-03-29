# coding:utf-8

from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            OptionsValidator, FolderValidator)


class Config(QConfig):
    workFolder = ConfigItem(
        "Folders", "WorkFolder", "work", FolderValidator())
    cacheFolder = ConfigItem(
        "Folders", "CacheFolder", "cache", FolderValidator())
    saveFolder = ConfigItem(
        "Folders", "SaveFolder", "save", FolderValidator())

    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)
    # software update
    checkUpdateAtStartUp = ConfigItem("Update", "UpdateAtStartUp", True, BoolValidator())
    # 保留原文
    keepOriginal = ConfigItem("BackFill", "KeepOriginal", False, BoolValidator())
    # 使用低版本lang格式
    lowVersionLangFormat = ConfigItem("LangFormat", "LowVersionLangFormat", False, BoolValidator())
    # 翻译API
    translateApi = OptionsConfigItem(
        "TranslateApi", "TranslateApi", "1", OptionsValidator(["0", "1", "2"]))
    appKey = ConfigItem("TranslateApi", "AppKey", 'Your APP_KEY')
    appSecret = ConfigItem("TranslateApi", "AppSecret", 'Your APP_SECRET')
    # openapi
    orgId = ConfigItem("TranslateApi", "OrgId", 'Your OrgId')
    secretKey = ConfigItem("TranslateApi", "SecretKey", 'Your SecretKey')
    openaiUrl = ConfigItem("OpenaiUrl", "OpenaiUrl", 'https://api.openai.com/v1')
    modelName = ConfigItem("ModelName", "ModelName", 'gpt-3.5-turbo')

    activateCode = ConfigItem("Activate", "ActivateCode", 'Your ActivateCode')
    # 游戏版本
    gameVersion = OptionsConfigItem("Meta", "GameVersion", "6", OptionsValidator(["1", "2", "3", "4", "11", "12",
                                                                                  "5", "6", "7", "8", "9", "13", "14",
                                                                                  "15"]))
    # 资源包名称
    metaName = ConfigItem("Meta", "Name", 'Modpack-Localization-Pack')
    # 资源包介绍
    metaDesc = ConfigItem("Meta", "Desc", 'generated by &aModpackLocalizationTools')
    # 资源包图标位置
    iconPath = ConfigItem("Meta", "Icon", "./work/pack.png")


YEAR = 2024
AUTHOR = "XDawned"
VERSION = 'v1.1.0'
HELP_URL = "https://github.com/XDawned"
REPO_URL = "https://github.com/XDawned"
EXAMPLE_URL = "https://github.com/XDawned"
FEEDBACK_URL = "https://github.com/XDawned/FTBQLocalizationTools/issues"
RELEASE_URL = "https://github.com/XDawned/FTBQLocalizationTools/releases/latest"
SUPPORT_URL = "https://afdian.net/a/XDawned"

cfg = Config()
qconfig.load('config/config.json', cfg)
