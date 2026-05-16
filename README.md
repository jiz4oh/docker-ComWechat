# docker-ComWechat
[![Publish to GHCR](https://github.com/jiz4oh/docker-ComWechat/actions/workflows/docker_build.yml/badge.svg)](https://github.com/jiz4oh/docker-ComWechat/actions/workflows/docker_build.yml)

A docker image for [ComWeChatRobot](https://github.com/ljc545w/ComWeChatRobot)


``` shell
docker run \
    --name comwechat  \
    --network host \
    -e VNCPASS=asdfgh123 \
    -e COMWECHAT=https://github.com/ljc545w/ComWeChatRobot/releases/download/3.7.0.30-0.0.5/3.7.0.30-0.0.5.zip \
    -dti  \
    --ipc=host \
    --privileged \
    -v $(pwd)/volume/WeChat\ Files/:'/home/user/.wine/drive_c/users/user/My Documents/WeChat Files/'  \
    -v $(pwd)/volume/Application\ Data:'/home/user/.wine/drive_c/users/user/Application Data/' \
    ghcr.io/jiz4oh/docker-comwechat
```

### 参数说明
* 端口 5905: VNC 服务的端口(无法/无需修改)
* network host: 使用宿主机网络(在 Linux Docker 环境下使用)
* 环境变量 VNCPASS: 连接 VNC 的密码（可自定义，建议在服务器上使用本镜像的话设置得难一点）
* 环境变量 COMWECHAT: [ComWeChatRobot](https://github.com/ljc545w/ComWeChatRobot/releases)具体版本的动态库文件压缩包(右键复制发布的文件的下载链接)【不设置此参数则默认为`3.7.0.30-0.0.5`的链接】
* 镜像仓库: `ghcr.io/jiz4oh/docker-comwechat`
* 目录映射 `WeChat Files`: 微信收到的图片/文件存储的目录(可以取消目录映射)
* 目录映射 `Application Data`: 微信数据目录(可以取消目录映射)

### 登录恢复点击
镜像内包含 `xdotool`，用于微信在运行过程中被服务端退出登录后自动点击登录按钮。首次启动后的扫码登录流程不会自动点击，仍通过 VNC 扫码登录。

可配置环境变量：
* `COMWECHAT_LOGIN_RECOVERY_CLICK`: 是否启用登录恢复点击，默认 `true`
* `COMWECHAT_LOGIN_STATE_INTERVAL`: 登录态检查间隔秒数，默认 `5`
* `COMWECHAT_LOGIN_CLICK_INTERVAL`: 点击重试间隔秒数，默认 `5`
* `COMWECHAT_LOGIN_RECOVERY_TIMEOUT`: 单次掉线后的点击恢复窗口秒数，默认 `300`
* `COMWECHAT_LOGIN_CLICK_X` / `COMWECHAT_LOGIN_CLICK_Y`: 指定绝对点击坐标，未设置时按微信窗口位置自动计算
* `COMWECHAT_LOGIN_CLICK_BOTTOM_OFFSET`: 自动计算坐标时距离窗口底部的偏移，默认 `90`

### 消息桥接扩展
镜像内置 `run2.py` 与 `comwechat_bridge.py`。默认入口为 `/run2.py`，启动后会先尝试读取 `COMWECHAT_RUNTIME_ZIP` 指向的压缩包，默认路径为 `/runtime-host/comwechat.zip`；如果文件不存在，则回退到 `COMWECHAT` 环境变量指定的 Release 压缩包下载流程。

启用桥接：
* `COMWECHAT_BRIDGE_ENABLED`: 是否启用桥接，默认关闭
* `COMWECHAT_BRIDGE_API_HOST`: 桥接 HTTP API 监听地址，默认 `0.0.0.0`
* `COMWECHAT_BRIDGE_API_PORT`: 桥接 HTTP API 端口，默认 `19088`
* `COMWECHAT_BRIDGE_IN_PORT`: ComWeChat hook 推送消息的内部端口，默认 `23456`
* `COMWECHAT_API_PORT`: ComWeChat HTTP API 端口，默认 `18888`

验证镜像时使用独立 compose，避免影响正在使用的 `comwechat`：

``` shell
docker build -t comwechat:click-test .
docker compose -p comwechat-click-test -f docker-compose.click-test.yaml up -d
docker logs --tail 160 comwechat-click-test
docker compose -p comwechat-click-test -f docker-compose.click-test.yaml down -v
```

## 如何使用
1. 运行上方命令启动镜像(更推荐使用 [docker-compose](./docker-compose.yaml) )
2. 连接上 VNC 扫码登陆微信(建议扫码登陆后把微信的版本号弹窗等关闭)
3. 使用 python 与微信通信(示例文件 [test.py](./test.py) )


## 鸣谢
[ljc545w/ComWeChatRobot](https://github.com/ljc545w/ComWeChatRobot): ComWeChatRobot 项目本体

[0honus0/ComWeChat_Inject](https://github.com/0honus0/ComWeChat_Inject): 本镜像所使用的注入器

## 相关项目
[efb-wechat-comwechat-slave](https://github.com/0honus0/efb-wechat-comwechat-slave): 使用 Telegram 来接收&管理微信消息

## 声明
**本项目仅供学习研究，强烈反对商业用途或者滥用(通过程序化控制微信对其他人进行骚扰诈骗等)！使用本项目造成的一切责任与本人无关，一切责任由使用者自行承担！**
