import sys
import time
import pymysql
import threading
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


class Database:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self, host=sys.argv[1], user=sys.argv[2], password=sys.argv[3], database=sys.argv[4]):
        if not hasattr(self, 'connection'):
            print('正在连接数据库...', flush=True)
            self.connection = pymysql.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
            self.cursor = self.connection.cursor()
            print('数据库连接成功。', flush=True)

    def execute(self, query, params=None):
        """执行数据库查询。"""
        print(f'正在执行查询: {query}', flush=True)
        self.cursor.execute(query, params)
        self.connection.commit()
        print('查询执行成功。', flush=True)

    def fetchall(self, query, params=None):
        """获取查询结果。"""
        print(f'正在获取查询结果: {query}', flush=True)
        self.cursor.execute(query, params)
        results = self.cursor.fetchall()
        print('查询结果获取成功。', flush=True)
        return results

    def close(self):
        """关闭数据库连接。"""
        print('正在关闭数据库连接...', flush=True)
        self.cursor.close()
        self.connection.close()
        print('数据库连接已关闭。', flush=True)


class BaidupanUpload:
    def __init__(self):
        print('正在初始化BaidupanUpload...', flush=True)
        chrome_options = Options()
        # 设置无头模式
        chrome_options.add_argument("--disable-dev-shm-usage")  # 解决资源限制问题

        # 连接到 Selenium 服务
        print('正在连接Selenium服务...', flush=True)
        self.browser = webdriver.Remote(
            command_executor='http://127.0.0.1:4444/wd/hub',
            options=chrome_options
        )
        self.db = Database()  # 初始化数据库连接
        print('BaidupanUpload初始化完成。', flush=True)

    def get(self, url):
        print(f'正在访问URL: {url}', flush=True)
        self.browser.get(url)
        print('访问完成。', flush=True)

    def login_by_cookie(self, cookie_string):
        print('正在使用Cookies登录...', flush=True)
        self.browser.get('https://pan.baidu.com/')
        # 删除本次打开网页时的所有 cookie
        self.browser.delete_all_cookies()

        # 解析 cookie 字符串并添加到浏览器
        cookies = self.parse_cookies(cookie_string)
        for cookie in cookies:
            self.browser.add_cookie(cookie)

        self.browser.refresh()
        self.browser.get('https://pan.baidu.com/disk/main?from=homeFlow#/index?category=all')
        print('登录账号成功。', flush=True)

    def parse_cookies(self, cookie_string):
        print('正在解析Cookies...', flush=True)
        cookies = []
        for cookie in cookie_string.split(';'):
            key_value = cookie.strip().split('=', 1)
            if len(key_value) == 2:
                key = key_value[0].strip()
                value = key_value[1].strip()
                cookies.append({'name': key, 'value': value})
        print(f'解析的Cookies: {cookies}', flush=True)
        return cookies

    def re_name(self):
        print('正在重命名文件...', flush=True)
        videos = self.db.fetchall(
            "SELECT a.id, a.video_name, b.title FROM success_download a, translation_title b WHERE a.id = b.video_id AND video_name NOT IN (SELECT pan_rename.video_name FROM pan_rename)"
        )
        print(f'找到 {len(videos)} 个待重命名的视频。', flush=True)
        for video in videos:
            search_input = self.browser.find_element(By.XPATH,
                                                     '//input[@type="text" and @placeholder="搜索我的文件" and @class="u-input__inner"]')
            search_input.clear()
            time.sleep(1)
            search_input.send_keys(video[1])
            self.browser.find_element(By.XPATH,
                                      '//span[@class="wp-s-search__search-text" and contains(text(), "搜索")]').click()
            time.sleep(3)
            trs = self.browser.find_elements(By.XPATH,
                                             '/html/body/div[1]/div[1]/div[2]/div[2]/div/div[1]/div/div[2]/div[1]/div[2]/div/div/div/div[2]/table/tbody/tr')
            if len(trs) == 0:
                self.db.execute("DELETE FROM baidu_pan_upload WHERE id = %s", (video[0],))
                print('删除未上传文件。', flush=True)
                continue
            elif len(trs) > 1:
                trs[0].click()
            else:
                self.browser.find_element(By.XPATH,
                                          '/html/body/div[1]/div[1]/div[2]/div[2]/div/div[1]/div/div[2]/div[1]/div[2]/div/div/div/div[1]/table/thead/tr/th[1]/label').click()

            self.browser.find_element(By.XPATH,
                                      value='/html/body/div[1]/div[1]/div[2]/div[2]/div/div[1]/div/div[1]/div/div[1]/div/div/div[1]/div/div[4]/button').click()
            time.sleep(2)
            self.browser.find_element(By.XPATH,
                                      value='/html/body/div[1]/div[1]/div[2]/div[2]/div/div[1]/div/div[2]/div[1]/div[2]/div/div/div/div[2]/table/tbody/tr/td[2]/div/div/div[1]/input').send_keys(
                f'{video[2]}[{video[1]}]')
            time.sleep(2)
            self.browser.find_element(By.XPATH,
                                      value='/html/body/div[1]/div[1]/div[2]/div[2]/div/div[1]/div/div[2]/div[1]/div[2]/div/div/div/div[2]/table/tbody/tr/td[2]/div/div/div[2]').click()
            search_input.clear()
            while True:
                try:
                    self.browser.find_element(By.XPATH, '/html/body/div[8]')
                    self.db.execute(
                        "INSERT INTO pan_rename (video_name) VALUES (%s)", (video[1],)
                    )
                    print('重命名完成。', flush=True)
                    break
                except NoSuchElementException:
                    time.sleep(1)
                    pass
        print('文件重命名过程完成。', flush=True)

    def get_share_from_baidupan(self):
        print('正在获取百度盘分享链接...', flush=True)
        videos = self.db.fetchall(
            "SELECT id, file_name FROM cj_data_by_hct WHERE upload_status = 1 AND share_url IS NULL"
        )

        print(f'找到 {len(videos)} 个视频以获取分享链接。', flush=True)
        for video in videos:
            search_input = self.browser.find_element(By.XPATH,
                                                     '//input[@type="text" and @placeholder="搜索我的文件" and @class="u-input__inner"]')
            search_input.clear()
            search_input.send_keys(video[1])
            self.browser.find_element(By.XPATH,
                                      '//span[@class="wp-s-search__search-text" and contains(text(), "搜索")]').click()
            time.sleep(3)
            trs = self.browser.find_elements(By.XPATH,
                                             '/html/body/div[1]/div[1]/div[2]/div[2]/div/div[1]/div/div[2]/div[1]/div[2]/div/div/div/div[2]/table/tbody/tr')
            if len(trs) == 0:
                self.db.execute("DELETE FROM cj_data_by_hct WHERE id = %s", (video[0],))
                print('删除未上传文件。', flush=True)
                continue
            elif len(trs) == 1:
                print('选中单个搜索结果。', flush=True)
                trs[0].click()
            else:
                print('选中全部搜索结果。', flush=True)
                self.browser.find_element(By.XPATH,
                                          '/html/body/div[1]/div[1]/div[2]/div[2]/div/div[1]/div/div[2]/div[1]/div[2]/div/div/div/div[1]/table/thead/tr/th[1]/label').click()
            time.sleep(0.3)
            share_buttons = self.browser.find_elements(By.XPATH,
                                                       '/html/body/div[1]/div[1]/div[2]/div[2]/div[2]/div[1]/div/div[1]/div/div[1]/div/div/div[1]/div/div/button')
            for button in share_buttons:
                if '分享' == button.text:
                    print('点击分享按钮。', flush=True)
                    button.click()
            time.sleep(1)
            wait = WebDriverWait(self.browser, 10)
            try:
                radio_label = wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="pane-link"]')))
                radio_label.find_element(By.XPATH,
                                         '//*[@id="pane-link"]/div/div[1]/div/form/div[1]/div/div/div/label[5]').click()
                time.sleep(1)
                self.browser.find_element(By.XPATH, '//*[@id="pane-link"]/div/div[1]/div/div[3]/button').click()
                wait_max_count = 10
                while True:
                    try:
                        self.browser.find_element(By.XPATH,
                                                  '//*[@id="pane-link"]/div/div[1]/div[1]/div[2]/div[1]/input').get_attribute(
                            'value')
                        print('等待分享链接', flush=True)
                        break
                    except:
                        wait_max_count -= 1
                        if wait_max_count <= 0:
                            break
                        continue
                if wait_max_count <= 0:
                    continue
                share_url = self.browser.find_element(By.XPATH,
                                                      '//*[@id="pane-link"]/div/div[1]/div[1]/div[2]/div[1]/input').get_attribute(
                    'value')
                share_pwd = self.browser.find_element(By.XPATH,
                                                      '//*[@id="pane-link"]/div/div[1]/div[1]/div[3]/div[2]/input').get_attribute(
                    'value')
                if share_pwd and share_url:
                    self.db.execute(
                        "UPDATE cj_data_by_hct SET share_url = %s, share_pwd = %s WHERE id = %s",
                        (share_url, share_pwd, video[0])
                    )
                    print(f'更新分享链接成功: {video[1]} {share_url}', flush=True)

                    try:
                        self.browser.find_element(By.XPATH,
                                                  '/html/body/div[1]/div[4]/div/div/div/div/div[1]/button').click()
                    except NoSuchElementException:
                        self.browser.find_element(By.XPATH,
                                                  '/html/body/div[1]/div[3]/div/div/div/div/div[1]/button').click()
                    time.sleep(1)
                    print(f'分享成功 ===== {video[1]} {share_url} =====', flush=True)
            except NoSuchElementException as E:
                print(E, '等待分享页面失败', flush=True)
                self.get_share_from_baidupan()
                return None, None
        print('分享链接获取完成。', flush=True)

    def check_and_close_popups(self):
        print('开始检查并关闭弹窗...', flush=True)
        while True:
            for xpath in [
                '/html/body/div[1]/div[1]/div[2]/div[1]/div/div[1]/div[1]/div/div[1]',
            ]:
                try:
                    popup = self.browser.find_element(By.XPATH, xpath)
                    if popup:
                        popup.click()
                        print(f'关闭弹窗: {xpath}', flush=True)
                except NoSuchElementException:
                    pass
            time.sleep(1)
        print('弹窗检查结束。', flush=True)


if __name__ == '__main__':
    print('程序开始运行...', flush=True)
    bd = BaidupanUpload()
    cookie = bd.db.fetchall("SELECT * FROM user_ck WHERE status = 1 and pan_name = 'baidu' limit 0,1")[0][1]
    bd.login_by_cookie(cookie)

    popup_thread = threading.Thread(target=bd.check_and_close_popups)
    popup_thread.daemon = True
    popup_thread.start()
    bd.get_share_from_baidupan()
    print('程序结束运行。', flush=True)
