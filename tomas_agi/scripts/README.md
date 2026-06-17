# TOMAS Flask 服务器 - 开机自启配置

本目录包含 Flask 服务器的启动脚本，支持 Windows 和 Linux 开机自启。

## Windows 配置

### 方法 1: 手动启动 (开发环境推荐)

双击运行 `start_flask.bat`，服务器将在后台启动。

### 方法 2: 计划任务 (开机自启)

1. 打开"任务计划程序" (Task Scheduler)
2. 创建新任务:
   - 名称: `TOMAS Flask Server`
   - 触发器: "启动时"
   - 操作: 执行 `start_flask.bat`
   - 条件: 取消勾选"只有在计算机使用交流电源时才启动此任务"
3. 保存并启用任务

### 方法 3: 批处理脚本 (简易自启)

将 `start_flask.bat` 的快捷方式放入:
- `shell:startup` (当前用户)
- `shell:common startup` (所有用户)

## Linux 配置 (systemd)

### 安装服务

```bash
# 复制 service 文件
sudo cp flask.service /etc/systemd/system/

# 重载 systemd
sudo systemctl daemon-reload

# 启用服务 (开机自启)
sudo systemctl enable flask.service

# 启动服务
sudo systemctl start flask.service

# 查看状态
sudo systemctl status flask.service

# 查看日志
sudo journalctl -u flask.service -f
```

### 管理服务

```bash
# 停止服务
sudo systemctl stop flask.service

# 重启服务
sudo systemctl restart flask.service

# 禁用开机自启
sudo systemctl disable flask.service
```

## 验证服务

访问 `http://localhost:5000/api/health` 确认服务器正常运行。

## 注意事项

1. **防火墙**: 确保端口 5000 已开放
2. **Python 环境**: 确保 Python 3.10+ 已安装且可用
3. **.env 文件**: 确保 `tomas_agi/sim/.env` 包含必要的配置 (如 `DEEPSEEK_API_KEY`)
4. **数据库**: 确保 `D:/tomas-data/tomas.db` 存在且可访问 (Windows) 或对应路径 (Linux)

## 故障排查

### Windows

- 查看"任务计划程序"中的任务运行历史
- 检查 Flask 进程是否在任务管理器中运行
- 查看 `tomas_agi/sim/` 目录下的日志文件 (如果有)

### Linux

```bash
# 查看服务状态
sudo systemctl status flask.service

# 查看详细日志
sudo journalctl -u flask.service --no-pager

# 测试手动启动
cd /root/tomas-agi/tomas_agi/sim
python3 server.py
```
