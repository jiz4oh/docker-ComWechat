#!/usr/bin/python3
import datetime
import json
import os
import signal
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from comwechat_bridge import BridgeConfig, BridgeService

version = os.environ.get('COMWECHAT_VERSION', '3.9.12.56')


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default

class DockerWechatHook:
    def __init__(self):
        signal.signal(signal.SIGINT, self.now_exit)
        signal.signal(signal.SIGHUP, self.now_exit)
        signal.signal(signal.SIGTERM, self.now_exit)
        self.bridge = None
        self.stop_event = threading.Event()
        self.login_clicker = None

    def now_exit(self, signum, frame):
        self.exit_container()

    def prepare(self):
        runtime_zip = os.environ.get("COMWECHAT_RUNTIME_ZIP", "/runtime-host/comwechat.zip")
        if os.path.exists(runtime_zip):
            self.prepare = subprocess.run(['unzip', '-o', '-d', '/comwechat', runtime_zip], check=False)
        elif not os.path.exists("/dll_downloaded.txt"):
            COMWECHAT = os.environ['COMWECHAT']
            if not COMWECHAT.startswith("https://github.com/ljc545w/ComWeChatRobot/releases/download/"):
                print("你提供的地址不是 COMWECHAT 仓库的 Release 下载地址，程序将自动退出！", flush=True)
                self.exit_container()
                sys.exit(1)
            self.prepare = subprocess.run(['wget', COMWECHAT, '-O', '/comwechat.zip'], check=False)
            self.prepare = subprocess.run(['unzip', '-o', '-d', '/comwechat', '/comwechat.zip'], check=False)
            with open("/dll_downloaded.txt", "w") as f:
                f.write("True\n")

        os.makedirs('/comwechat/http', mode=755, exist_ok=True)
        self.prepare = subprocess.run(['cp', '/WeChatHook.exe', '/comwechat/http/WeChatHook.exe'], check=False)

    def run_vnc(self):
        # 根据 VNCPASS 环境变量生成 vncpasswd 文件
        os.makedirs('/root/.vnc', mode=755, exist_ok=True)
        passwd_output = subprocess.run(['/usr/bin/vncpasswd','-f'],input=os.environ['VNCPASS'].encode(),capture_output=True)
        with open('/root/.vnc/passwd', 'wb') as f:
            f.write(passwd_output.stdout)
        os.chmod('/root/.vnc/passwd', 0o700)
        self.vnc = subprocess.Popen(['/usr/bin/vncserver','-localhost',
            'no', '-xstartup', '/usr/bin/openbox' ,':5'])

    def run_wechat(self):
        # if not os.path.exists("/wechat_installed.txt"):
        #     self.wechat = subprocess.run(['wine','WeChatSetup.exe'])
        #     with open("/wechat_installed.txt", "w") as f:
        #         f.write("True\n")
        # self.wechat = subprocess.run(['wine', 'explorer.exe'])
        self.wechat = subprocess.Popen(['wine','/home/user/.wine/drive_c/Program Files/Tencent/WeChat/WeChat.exe'])
        # self.wechat = subprocess.run(['wine','/home/user/.wine/drive_c/Program Files/Tencent/WeChat/WeChat.exe'])

    def run_hook(self):
        print("等待 5 秒再 hook", flush=True)
        time.sleep(5)
        self.reg_hook = subprocess.Popen(['wine','/comwechat/http/WeChatHook.exe'])
        # self.reg_hook = subprocess.run(['wine', 'explorer.exe'])

    def change_version(self):
        time.sleep(5)
        result = subprocess.run(['curl', '-X', 'POST', 'http://127.0.0.1:18888/api/?type=35', '-H', 'Content-Type: application/json', '-d', json.dumps({"path": "/comwechat/http/WeChatHook.exe", "version": version})], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"Curl command failed with error: {result.stderr.decode()}", flush=True)
            print("版本修改失败", flush=True)
            self.exit_container()
            sys.exit(1)
        else:
            print("版本已经修改", flush=True)

    def start_login_recovery_clicker(self):
        if not env_bool("COMWECHAT_LOGIN_RECOVERY_CLICK", True):
            print("登录恢复点击已关闭", flush=True)
            return
        if shutil.which("xdotool") is None:
            print("未找到 xdotool，登录恢复点击不可用", flush=True)
            return

        self.login_clicker = threading.Thread(
            target=self.login_recovery_clicker,
            daemon=True,
            name="login-recovery-clicker",
        )
        self.login_clicker.start()

    def login_recovery_clicker(self):
        api_port = env_int("COMWECHAT_API_PORT", 18888)
        state_interval = env_float("COMWECHAT_LOGIN_STATE_INTERVAL", 5)
        click_interval = env_float("COMWECHAT_LOGIN_CLICK_INTERVAL", 5)
        recovery_timeout = env_float("COMWECHAT_LOGIN_RECOVERY_TIMEOUT", 300)

        seen_logged_in = False
        recovery_deadline = None
        next_click_at = 0

        print("登录恢复点击监控已启动：首次扫码登录阶段不会点击", flush=True)
        while not self.stop_event.is_set():
            is_login = self.get_login_state(api_port)
            now = time.monotonic()

            if is_login is True:
                if not seen_logged_in:
                    print("已确认首次登录，后续掉线会启用登录恢复点击", flush=True)
                seen_logged_in = True
                recovery_deadline = None
                next_click_at = 0
            elif is_login is False and seen_logged_in:
                if recovery_deadline is None:
                    recovery_deadline = now + recovery_timeout
                    print("检测到登录态丢失，开始尝试点击登录按钮", flush=True)

                if now <= recovery_deadline and now >= next_click_at:
                    self.click_login_button()
                    next_click_at = now + click_interval
                elif now > recovery_deadline:
                    print("登录恢复点击超时，等待登录态再次变化", flush=True)
                    recovery_deadline = None

            self.stop_event.wait(state_interval)

    def get_login_state(self, api_port):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{api_port}/api/?type=0",
                timeout=2,
            ) as response:
                payload = json.loads(response.read().decode())
            return bool(payload.get("is_login"))
        except Exception as e:
            print(f"登录态检查失败: {e}", flush=True)
            return None

    def click_login_button(self):
        window_id = self.find_wechat_window()
        if not window_id:
            print("未找到微信窗口，跳过本次登录恢复点击", flush=True)
            return False

        geometry = self.get_window_geometry(window_id)
        if not geometry:
            print(f"无法读取微信窗口几何信息: {window_id}", flush=True)
            return False

        x, y, width, height = geometry
        click_x = env_int("COMWECHAT_LOGIN_CLICK_X", x + width // 2)
        click_y = env_int(
            "COMWECHAT_LOGIN_CLICK_Y",
            y + height - env_int("COMWECHAT_LOGIN_CLICK_BOTTOM_OFFSET", 90),
        )

        env = os.environ.copy()
        env["DISPLAY"] = os.environ.get("DISPLAY", ":5")
        subprocess.run(["xdotool", "windowactivate", "--sync", window_id], env=env, check=False)
        result = subprocess.run(
            ["xdotool", "mousemove", "--sync", str(click_x), str(click_y), "click", "1"],
            env=env,
            check=False,
        )
        if result.returncode == 0:
            print(f"已尝试点击登录按钮: window={window_id} x={click_x} y={click_y}", flush=True)
            return True

        print(f"点击登录按钮失败: window={window_id} code={result.returncode}", flush=True)
        return False

    def find_wechat_window(self):
        env = os.environ.copy()
        env["DISPLAY"] = os.environ.get("DISPLAY", ":5")
        candidates = []
        for command in (
            ["xdotool", "search", "--onlyvisible", "--name", "微信|WeChat"],
            ["xdotool", "search", "--name", "微信|WeChat"],
            ["xdotool", "search", "--onlyvisible", "--class", "wechat.exe|WeChat.exe|WeChat"],
        ):
            result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
            if result.returncode == 0:
                candidates.extend(line.strip() for line in result.stdout.splitlines() if line.strip())

        for window_id in reversed(list(dict.fromkeys(candidates))):
            if self.get_window_geometry(window_id):
                return window_id
        return None

    def get_window_geometry(self, window_id):
        env = os.environ.copy()
        env["DISPLAY"] = os.environ.get("DISPLAY", ":5")
        result = subprocess.run(
            ["xdotool", "getwindowgeometry", "--shell", window_id],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            return None

        values = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value

        try:
            return (
                int(values["X"]),
                int(values["Y"]),
                int(values["WIDTH"]),
                int(values["HEIGHT"]),
            )
        except (KeyError, ValueError):
            return None

    def exit_container(self):
        self.stop_event.set()
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+ ' 正在退出容器...', flush=True)
        try:
            if self.bridge is not None:
                print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+ ' 停止消息桥接...', flush=True)
                self.bridge.stop()
        except Exception as e:
            print(f"停止消息桥接异常: {e}", flush=True)
        try:
            print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+ ' 退出微信...', flush=True)
            os.kill(self.wechat.pid, signal.SIGTERM)
        except:
            pass
        try:
            print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+ ' 退出Hook程序...', flush=True)
            os.kill(self.reg_hook.pid, signal.SIGTERM)
        except:
            pass
        try:
            print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+ ' 退出VNC...', flush=True)
            os.kill(self.vnc.pid, signal.SIGTERM)
        except:
            pass

    def run_all_in_one(self):
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+ ' 启动容器中...', flush=True)
        self.prepare()
        self.run_vnc()
        self.run_wechat()
        self.run_hook()
        self.change_version()
        self.bridge = BridgeService(BridgeConfig.from_env())
        self.bridge.start()
        self.start_login_recovery_clicker()
        while True:
            time.sleep(1)
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+ ' 感谢使用.', flush=True)


if __name__ == '__main__' :
    print('---All in one 微信 ComRobot 容器---', flush=True)
    hook = DockerWechatHook()
    hook.run_all_in_one()
