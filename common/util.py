import difflib
import hashlib
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

import requests
import snbtlib
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from transformers import MarianTokenizer, MarianMTModel

from common.config import cfg

MAGIC_WORD = r'{xdawned}'  # 先在术语库中记录，保证其不被翻译


def parse_json_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.loads(f.read())
    return data


def save_file(data_, path):
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        time.sleep(0.1)
    with open(path, 'w', encoding='utf-8') as f:
        # json.dump(data_, f, indent=4, ensure_ascii=False)
        f.write(data_)


def save_lang_file(data_: dict, path: str, text: str = None):
    if path.endswith('.lang'):
        with open(path, 'w', encoding='utf-8') as f:
            for key, value in data_.items():
                value = json.dumps(value, ensure_ascii=False)
                f.write(f'{key}={value}\n')
    elif path.endswith('.json'):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data_, f, indent=1, ensure_ascii=False)
    elif path.endswith('.snbt'):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)


def check_file_exists(directory_path, file_name):
    if os.path.exists(os.path.join(directory_path, file_name)):
        return directory_path + '/' + file_name
    else:
        return None


def get_if_subfolder_exists(directory, target_folder):
    target_folder_parts = target_folder.split('/')
    root_folder = target_folder_parts[0]
    sub_folders = target_folder_parts[1:]

    for root, dirs, files in os.walk(directory):
        if root.endswith(root_folder) and all(sub_folder in dirs for sub_folder in sub_folders):
            return os.path.normpath(os.path.join(root, *sub_folders))

    return None


def merge_dicts(dict1, dict2):
    merged_dict = {}

    for key, value in dict1.items():
        merged_dict[key] = value

    for key, value in dict2.items():
        if key in merged_dict:
            # 处理重叠的键
            new_key = key + "_"  # 重叠则以原有键为基础添加后缀"_"
            merged_dict[new_key] = value
        else:
            merged_dict[key] = value

    return merged_dict


def get_if_folder_exists(directory, target_folder):
    for root, dirs, files in os.walk(directory):
        if target_folder in dirs:
            return os.path.normpath(os.path.join(root, target_folder))
    return None


def encode_to_MD5(filepath):
    print(filepath)
    stat = os.stat(filepath)
    size = stat.st_size

    identifier = hashlib.md5(str(size).encode()).hexdigest()

    return identifier


def find_similar_terms(term, term_dict):
    matches = difflib.get_close_matches(term, term_dict.keys(), n=50, cutoff=0.6)
    similar_terms = {match: term_dict[match] for match in matches}
    return similar_terms


class FTBQuest:
    input_path = None
    prefix = ''
    text = ''
    quest = {}
    lang = {}
    quest_local = {}
    low = False

    def __init__(self, p: str):
        self.lang = {}
        self.input_path = Path(p)
        self.prefix = '' + list(self.input_path.parts)[-1].replace('.snbt', '')
        with open(p, 'r', encoding="utf-8") as fin:
            text = fin.read()
            self.text = text
            self.low = self.check_low()
            try:
                quest = snbtlib.loads(text)
                self.quest = quest
                self.quest_local = quest
                self.getLang()
            except TypeError:
                print('snbtlib调用出错，可能是python环境版本过低或其它问题！')
                sys.exit(0)

    def check_low(self):
        match = re.search(r',\n(?!")', self.text)
        if match:
            return True
        else:
            return False

    def dumps(self, dic: dict):
        quest_local_text = snbtlib.dumps(dic, compact=self.low)
        quest_local_text.replace('"B;"', 'B;')
        return quest_local_text

    @staticmethod
    def getValue(prefix: str, text: str):
        key_value = {}
        if isinstance(text, list):
            for i in range(0, len(text)):
                if bool(re.search(r'\S', text[i])):
                    if text[i].find('{image:') == -1:
                        local_key = prefix + '.' + str(i)
                        key_value[local_key] = text[i]
                        text[i] = '{' + local_key + '}'
            return text, key_value
        else:
            if text.find('{image:') == -1:
                key_value[prefix] = text
                text = '{' + prefix + '}'
            return text, key_value

    def getLang(self):
        prefix = self.prefix
        if self.quest.get('chapter_groups'):
            chapter_groups = self.quest['chapter_groups']
            for i in range(0, len(chapter_groups)):
                local_key = 'ftbquests.chapter_groups.' + prefix + '.' + str(i) + '.title'
                text, new_lang = self.getValue(local_key, chapter_groups[i]['title'])
                self.lang.update(new_lang)
                self.quest_local['chapter_groups'][i]['title'] = text
        elif self.quest.get('loot_size'):
            title = self.quest['title']
            local_key = 'ftbquests.reward_tables.' + prefix + '.title'
            text, new_lang = self.getValue(local_key, self.quest['title'])
            self.lang.update(new_lang)
            self.quest_local['title'] = text
        elif self.quest.get('disable_gui'):
            if self.quest.get('title'):
                local_key = 'ftbquests.data.' + prefix + '.title'
                text, new_lang = self.getValue(local_key, self.quest['title'])
                self.lang.update(new_lang)
                self.quest['title'] = text
        else:
            if self.quest.get('title'):
                title = self.quest['title']
                local_key = 'ftbquests.chapter.' + prefix + '.title'
                text, new_lang = self.getValue(local_key, self.quest['title'])
                self.lang.update(new_lang)
                self.quest_local['title'] = text
            if self.quest.get('subtitle'):
                subtitle = self.quest['subtitle']
                if len(subtitle) > 0:
                    local_key = 'ftbquests.chapter.' + prefix + '.subtitle'
                    text, new_lang = self.getValue(local_key, self.quest['subtitle'])
                    self.lang.update(new_lang)
                    self.quest_local['subtitle'] = text
            if self.quest.get('text'):
                if len(self.quest['text']) > 0:
                    local_key = 'ftbquests.chapter.' + prefix + '.text'
                    text, new_lang = self.getValue(local_key, self.quest['text'])
                    self.lang.update(new_lang)
                    self.quest['text'] = text
            if self.quest.get('images'):
                images = self.quest['images']
                for i in range(0, len(images)):
                    if images[i].get('hover'):
                        hover = images[i]['hover']
                        if len(hover) > 0:
                            local_key = 'ftbquests.chapter.' + prefix + '.images.' + str(i) + '.hover'
                            text, new_lang = self.getValue(local_key, hover)
                            self.lang.update(new_lang)
                            self.quest_local['images'][i]['hover'] = text
            if self.quest.get('quests'):
                quests = self.quest['quests']
                for i in range(0, len(quests)):
                    # title
                    if quests[i].get('title'):
                        title = quests[i]['title']
                        if len(title) > 0:
                            local_key = 'ftbquests.chapter.' + prefix + '.quests.' + str(i) + '.title'
                            text, new_lang = self.getValue(local_key, title)
                            self.lang.update(new_lang)
                            self.quest_local['quests'][i]['title'] = text
                    if quests[i].get('subtitle'):
                        subtitle = quests[i]['subtitle']
                        if len(subtitle) > 0:
                            local_key = 'ftbquests.chapter.' + prefix + '.quests.' + str(i) + '.subtitle'
                            text, new_lang = self.getValue(local_key, subtitle)
                            self.lang.update(new_lang)
                            self.quest_local['quests'][i]['subtitle'] = text
                    if quests[i].get('description'):
                        description = quests[i]['description']
                        if len(description) > 0:
                            local_key = 'ftbquests.chapter.' + prefix + '.quests.' + str(i) + '.description'
                            text, new_lang = self.getValue(local_key, description)
                            self.lang.update(new_lang)
                            self.quest_local['quests'][i]['description'] = text
                    if quests[i].get('text'):
                        if len(quests[i]['text']) > 0:
                            local_key = 'ftbquests.chapter.' + prefix + '.quests.' + str(i) + '.text'
                            text, new_key_value = self.getValue(local_key, quests[i]['text'])
                            self.lang.update(new_key_value)
                            self.quest['quests'][i]['text'] = text
                    if quests[i].get('tasks'):
                        tasks = quests[i]['tasks']
                        if len(tasks) > 0:
                            for j in range(0, len(tasks)):
                                if tasks[j].get('title'):
                                    title = tasks[j]['title']
                                    local_key = 'ftbquests.chapter.' + prefix + '.quests.' + str(i) + '.tasks.' + str(
                                        j) + '.title'
                                    text, new_lang = self.getValue(local_key, title)
                                    self.lang.update(new_lang)
                                    self.quest_local['quests'][i]['tasks'][j]['title'] = text

                    if quests[i].get('tasks'):
                        tasks = quests[i]['tasks']
                        if len(tasks) > 0:
                            for j in range(0, len(tasks)):
                                if tasks[j].get('description'):
                                    description = tasks[j]['description']
                                    local_key = 'ftbquests.chapter.' + prefix + '.quests.' + str(i) + '.tasks.' + str(
                                        j) + '.description'
                                    text, new_lang = self.getValue(local_key, description)
                                    self.lang.update(new_lang)
                                    self.quest_local['quests'][i]['tasks'][j]['description'] = text

                    if quests[i].get('rewards'):
                        rewards = quests[i]['rewards']
                        if len(rewards) > 0:
                            for j in range(0, len(rewards)):
                                if rewards[j].get('title'):
                                    title = rewards[j]['title']
                                    local_key = 'ftbself.quests.chapter.' + prefix + '.quests.' + str(
                                        i) + '.rewards.' + str(
                                        j) + '.title'
                                    text, new_lang = self.getValue(local_key, title)
                                    self.lang.update(new_lang)
                                    self.quest_local['quests'][i]['rewards'][j]['title'] = text

    def backFill(self, lang_: dict):
        text_ = snbtlib.dumps(self.quest_local)
        for key, value in lang_.items():
            text_ = text_.replace('{' + key + '}', str(value))
        return text_


class BetterQuest:
    input_path = None
    quest = {}
    lang = {}
    quest_local = {}

    def __init__(self, p: str):
        self.input_path = p
        self.quest = parse_json_file(p)
        self.quest_local, self.lang, _, _ = self.traverse_trans(self.quest)

    def traverse_trans(self, dictionary: dict, key_value=None, name_index=0, desc_index=0):
        if key_value is None:
            key_value = {}
        for key in dictionary.keys():
            if isinstance(dictionary[key], dict):

                dictionary[key] = dictionary_
            else:
                dictionary_, key_value, name_index, desc_index = self.traverse_trans(dictionary[key], key_value, name_index, desc_index)
                if dictionary[key] == "":
                    continue
                elif key.find('name:') != -1:
                    key_content = 'bq.name.' + str(name_index)
                    name_index += 1
                elif key.find('desc:') != -1:
                    key_content = 'bq.desc.' + str(desc_index)
                    desc_index += 1
                else:
                    continue
                key_value[key_content] = dictionary[key]
                dictionary[key] = key_content

        return dictionary, key_value, name_index, desc_index

    def backFill(self, lang_: dict):
        text_ = json.dumps(self.quest_local, indent=4, ensure_ascii=False)
        for key, value in lang_.items():
            text_ = text_.replace(key, str(value))
        return text_

    def dumps(self, dic: dict):
        text = json.dumps(dic, indent=1, ensure_ascii=False)
        return text


class Translator(QObject):
    from_lang = ''
    to_lang = ''
    app_key = ''
    app_secret = ''
    model = None
    tokenizer = None
    spec_format = pyqtSignal(str)

    def __init__(self, from_lang: str, to_lang: str, key: str, secret: str):
        super().__init__()
        self.from_lang = from_lang
        self.to_lang = to_lang
        self.app_key = key
        self.app_secret = secret

    @staticmethod
    def bracket(m: re.Match):
        return "[&" + m.group(0) + "]"

    @staticmethod
    def debracket(m: re.Match):
        return m.group(0)[2:-1]

    def pre_process(self, line: str):
        if line.find('.jpg') + line.find('.png') != -2:
            self.spec_format.emit('注意:检测到图片格式，不翻译')
            return None
        if line.find(r'{\"') != -1:
            return None
        line = line.replace('\\\\&', 'PPP')
        if self.model is None:
            pattern = re.compile(r'&([a-z,0-9]|#[0-9,A-F]{6})')
            line = pattern.sub(self.bracket, line)
            self.spec_format.emit('注意:检测到彩色字符已预处理，不保证100%保留')
        line = re.sub(r'#\w+:\w+\b', MAGIC_WORD, re.sub(r'\\"', '\"', line))
        pattern = re.compile(r'(http|https)://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')
        if re.search(pattern, line):
            self.spec_format.emit('注意:检测到包含网址，不翻译')
            return None
        return line

    def post_process(self, text_, translate, original=False):
        if self.model is None:
            pattern = re.compile(r'\[&&([a-z,0-9]|#[0-9,A-F]{6})]')
            translate = pattern.sub(self.debracket, translate)
            text_ = pattern.sub(self.debracket, text_)
        text_ = re.sub(r'(["\'])', r'\\\g<1>', text_)
        quotes = re.findall(r'#\w+:\w+\b', text_)
        if len(quotes) > 0:
            self.spec_format.emit('注意:检测到物品引用已处理，不保证100%安全')
            count = 0
            index = translate.find(MAGIC_WORD)
            while index != -1:
                translate = re.sub(MAGIC_WORD, quotes[count], translate, 1)
                count = count + 1
                index = translate.find(MAGIC_WORD)
        if original:
            replacement = translate + "[--" + text_ + "--]"
            return replacement
        return translate

    def baiduTranslate(self, text_: str, original=False):
        text_process = self.pre_process(text_)
        if text_process is None:
            return text_
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.app_key,
            "client_secret": self.app_secret
        }
        response = requests.get(url, params=params)
        result = response.json()
        access_token = result["access_token"]

        url_ = "https://aip.baidubce.com/rpc/2.0/mt/texttrans/v1"
        headers = {
            "Content-Type": "application/json;charset=utf-8"
        }
        body = {
            "from": self.from_lang,
            "to": self.to_lang,
            "q": text_process
        }
        params_ = {
            "access_token": access_token
        }
        response_ = requests.post(url_, headers=headers, params=params_, json=body)
        result_ = response_.json()
        try:
            translated_text = result_["result"]["trans_result"][0]["dst"]
        except Exception as e:
            translated_text = ""

        return self.post_process(text_, translated_text, original)

    def init_local_model(self):
        self.model = MarianMTModel.from_pretrained("./models/minecraft-en-zh")
        self.tokenizer = MarianTokenizer.from_pretrained("./models/minecraft-en-zh")

    def localTranslate(self, text_: str, original=False):
        text_process = self.pre_process(text_)
        if text_process is None:
            return text_
        input_ids = self.tokenizer.encode(text_process, return_tensors="pt")
        translated = self.model.generate(input_ids, max_length=128)
        output = self.tokenizer.decode(translated[0], skip_special_tokens=True)
        return self.post_process(text_, output, original)


class LangTranslatorThread(QThread):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    index = pyqtSignal(str)
    info = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, lang, from_lang, to_lang, app_key, app_secret, keepOriginal):
        super().__init__()
        self.lang = lang
        self.translator = Translator(from_lang, to_lang, app_key, app_secret)
        self.keepOriginal = keepOriginal

    def run(self):
        try:
            api = cfg.get(cfg.translateApi)
            self.translator.spec_format.connect(self.handle_emit_process_info)
            if api == '1':
                self.translator.init_local_model()
            count = len(self.lang)
            str_count = 0
            for index in range(0, count):
                progress = (index + 1) / count * 100
                str_count += len(self.lang[index][1])
                self.progress.emit(progress)
                self.index.emit('翻译进度:%s,已耗字符：%s' % (str(index + 1), str(str_count)))
                self.info.emit('正在翻译:%s' % self.lang[index][1])
                trans = 'ChatGPT翻译尚在开发中，敬请期待！'
                if api == '0':
                    trans = self.translator.baiduTranslate(self.lang[index][1], self.keepOriginal)
                elif api == '1':
                    trans = self.translator.localTranslate(self.lang[index][1], self.keepOriginal)
                self.lang[index][2] = trans
                self.lang[index][3] = trans
                self.info.emit('翻译结果为:%s' % trans)
        except Exception as e:
            self.error.emit(str(e))
        else:
            self.finished.emit()

    def stop(self):
        self.terminate()
        self.wait()
        self.finished.emit()

    def handle_emit_process_info(self, info: str):
        self.info.emit(info)


class Lang:
    def __init__(self):
        self.file_path = ''
        self.lang_dic = {}
        self.cache_dic = {}
        self.cache_name = ''
        self.cache_folder = ''
        self.cache_file_path = ''
        self.lang_bilingual_list = []

    def read_lang(self, file_path: str, cache: bool = False):
        self.__init__()
        self.cache_folder = cfg.get(cfg.cacheFolder)
        self.file_path = file_path
        # 读取数据
        # 兼容lang或json类型语言文件
        if file_path.endswith('.lang'):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                lang_data = f.read()
                # 清理注释
                lang_data = '\n'.join(line for line in lang_data.split('\n') if not line.strip().startswith("#"))
                # 分割键值对
                lang_data = [line.strip() for line in lang_data.split('\n') if line.strip()]
                for line in lang_data:
                    key, value = line.split("=", maxsplit=1)
                    self.lang_dic[key.strip()] = value.strip()
        elif file_path.endswith('.json'):
            self.lang_dic = parse_json_file(file_path)
        if cache:
            self.init_cache()
        self.init_bilingual()

    def set_lang(self, data: dict):
        self.__init__()
        self.lang_dic = data
        self.init_bilingual()

    def init_cache(self, cache_name: str = None, cache_folder: str = None):
        if cache_name and cache_folder:
            self.cache_name = cache_name
            self.cache_folder = cache_folder
        else:
            self.cache_name = encode_to_MD5(self.file_path) + '.json'
        self.cache_file_path = self.cache_folder + '/' + self.cache_name
        if check_file_exists(self.cache_folder, self.cache_name) is not None:
            self.cache_dic = parse_json_file(self.cache_file_path)
        else:
            save_lang_file({}, self.cache_file_path)

    def init_bilingual(self):
        self.lang_bilingual_list = []
        for key, value in self.lang_dic.items():
            if self.cache_dic.get(key):
                self.lang_bilingual_list.append([key, value, self.cache_dic[key]['trans'], ''])
            else:
                self.lang_bilingual_list.append([key, value, '', ''])

    # def migrate(self, en_us_path, zh_cn_path):
    #
    #     en_us_lang = Lang()
    #     zh_cn_lang = Lang()
    #     en_us_lang.read_lang(en_us_path)
    #     zh_cn_lang.read_lang(zh_cn_path)
    #     for key, value in self.lang_dic.items():
    #         # 检查新版本中的原文是否与旧版本相同
    #         if key in old_data and old_data[key] == value:
    #             # 如果相同，将对应的翻译从旧版本语言文件迁移到新版本中
    #             updated_data[key] = old_data[key]
    #         else:
    #             # 如果不同，保留新版本中的翻译
    #             updated_data[key] = value

    def save_cache(self):
        self.cache_dic = {}
        for i in range(len(self.lang_bilingual_list)):
            if self.lang_bilingual_list[i][2] != '':
                key = self.lang_bilingual_list[i][0]
                self.cache_dic[key] = {}
                self.cache_dic[key]['ori'] = self.lang_bilingual_list[i][1]
                self.cache_dic[key]['trans'] = self.lang_bilingual_list[i][2]
        save_lang_file(self.cache_dic, self.cache_file_path)
        return self.cache_file_path


class Mod:
    def __init__(self, path):
        self.path = path
        self.modName = ''
        self.langList = []
        self.get_info()

    def get_info(self):
        with zipfile.ZipFile(self.path, 'r') as jar:
            for file_info in jar.infolist():
                name = file_info.filename
                match1 = re.search(r"assets/([^/]+)", name)
                if match1:
                    self.modName = match1.group(1)
                match2 = re.search(r"lang/([^/]+)", name)
                if match2:
                    self.langList.append(match2.group(1))

    def get_lang_text(self, lang_name: str):
        with zipfile.ZipFile(self.path, 'r') as jar:
            for file_info in jar.infolist():
                name = file_info.filename
                if (r'lang/' + lang_name) in name:
                    with jar.open(name) as json_file:
                        content = json_file.read().decode('latin-1')
                        return content


class ResourcePack:
    def __init__(self, path: str):
        self.mods = []
        self.path = path
        self.get_mods_with_i18n()

    def get_mods_with_i18n(self):
        with zipfile.ZipFile(self.path, 'r') as file:
            for file_info in file.infolist():
                name = file_info.filename
                match1 = re.search(r"assets/([^/]+)", name)
                if match1:
                    if r'lang/zh_cn.' in name:
                        mod = match1.group(1)
                        if mod not in self.mods:
                            self.mods.append(mod)
