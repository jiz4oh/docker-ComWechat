# Agent 工作说明

## 包管理器
- 本仓库只使用 `docker`、`docker compose` 和少量 `python3` 静态检查。
- 镜像发布由 `.github/workflows/docker_build.yml` 推送到 `ghcr.io/jiz4oh/docker-comwechat`。

## 文件级命令
| 任务 | 命令 |
|---|---|
| Python 入口检查 | `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile run.py comwechat_bridge.py` |
| Compose 配置检查 | `docker compose -f docker-compose.yaml config --quiet` |
| 镜像冒烟测试 | `bash tests/smoke_test.sh` |
| 查看已发布镜像 | `docker buildx imagetools inspect ghcr.io/jiz4oh/docker-comwechat:latest` |

## 仓库地图
- `Dockerfile`：Wine、WeChat、VNC、`xdotool`、`run.py`、`comwechat_bridge.py` 的镜像打包入口。
- `run.py`：容器默认入口，负责准备 ComWeChat 产物、启动 VNC/WeChat/hook、登录恢复点击和 bridge。
- `comwechat_bridge.py`：消息 hook 接收、重排缓冲、pull API 和 bridge 健康检查。
- `docker-compose.yaml`：本项目示例运行配置，使用 GHCR 镜像。
- `tests/smoke_test.sh`：本仓库冒烟测试，会临时生成隔离 compose 并自动清理容器和卷。
- `VERSION`：GHCR 版本 tag 来源。

## 关键约定
- 默认入口是 `/run.py`；不要恢复 `run2.py`，也不要在 compose 中挂载外部 `run2.py` 或 `comwechat_bridge.py`。
- `COMWECHAT_RUNTIME_ZIP` 默认读取 `/runtime-host/comwechat.zip`；挂载时只挂这个 zip 文件即可。
- 登录恢复点击只用于已登录后被服务端退出登录的恢复流程；首次扫码登录仍通过 VNC 手动扫码。
- bridge 默认可由 `COMWECHAT_BRIDGE_ENABLED` 控制；compose 联调需要显式开启并检查 `/healthz`。
- 不要保留专用 `docker-compose.click-test.yaml`；测试 compose 只能由测试脚本临时生成。
- 修改 `Dockerfile`、`run.py`、`comwechat_bridge.py` 或 compose 后，至少完成 Python 编译、compose config 和 `bash tests/smoke_test.sh`。
- 发布前更新 `VERSION`，推送后确认 GHCR `latest` 与版本 tag 的 manifest。
