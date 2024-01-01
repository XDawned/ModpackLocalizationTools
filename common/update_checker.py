import requests

from common.config import cfg, VERSION


class UpdateChecker:
    latest_version = ''
    logs = ''
    link = ''
    need_update = False

    def __init__(self):
        if cfg.get(cfg.checkUpdateAtStartUp):
            self.check()

    def check(self):
        url = 'https://mockapi.eolink.com/xTErhAwc4668071e4e0351ac3a2e20131a45027fac017a0/version?responseId=1346980'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                result = response.json()
                self.latest_version = result.get('latest_version')
                self.logs = result.get('logs')
                self.link = result.get('link')
                if self.latest_version != VERSION:
                    self.need_update = True
        except Exception as e:
            print(e)


update_checker = UpdateChecker()
