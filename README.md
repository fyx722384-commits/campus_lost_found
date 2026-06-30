# 校园失物招领信息管理系统

这是一个用于《面向对象软件开发课程设计》的本地 Web 原型系统，技术栈为 Python + Flask + SQLite + HTML/CSS/JavaScript。

## 运行步骤

```bash
pip install -r requirements.txt
python seed_data.py
python app.py
```

本机浏览器访问：

```text
http://127.0.0.1:5000/login
```

## 局域网访问说明

启动项目：

```bash
python seed_data.py
python app.py
```

本机访问：

```text
http://127.0.0.1:5000/login
```

查询本机 IPv4 地址：

1. 打开 CMD。
2. 输入：

```bash
ipconfig
```

3. 找到当前正在使用的网络，例如“无线局域网适配器 WLAN”。
4. 找到 `IPv4 地址`，例如 `10.23.45.67` 或 `192.168.1.23`。

同一 Wi-Fi / 同一局域网下，其他设备访问：

```text
http://你的IPv4地址:5000/login
```

如果我的 IPv4 是 `10.23.45.67`，那么分享给别人的是：

```text
http://10.23.45.67:5000/login
```

注意事项：

1. 不能把 `http://127.0.0.1:5000/login` 分享给别人，因为 `127.0.0.1` 只代表访问者自己的电脑。
2. 别人访问时，你的电脑必须保持 `python app.py` 正在运行。
3. 你和对方最好连接同一个 Wi-Fi 或同一个局域网。
4. 如果都连接校园网但仍打不开，可能是校园网开启了设备隔离，这不是代码问题。
5. 如果打不开，需要检查 Windows 防火墙是否允许 Python 通过网络。
6. 如果校园网无法互通，可以尝试使用手机热点、使用同一个宿舍路由器、使用内网穿透，或部署到公网平台。

防火墙检查路径：

```text
Windows 安全中心 → 防火墙和网络保护 → 允许应用通过防火墙
```

找到 `Python` 或 `python.exe`，允许它通过专用网络和公用网络。

## Render 公网部署说明

部署到 Render 后，其他人可以通过公网网址访问系统，例如：

```text
https://你的项目名.onrender.com/login
```

部署步骤：

1. 将当前项目上传到 GitHub 仓库。
2. 打开 Render，选择 `New Web Service`。
3. 连接 GitHub 仓库，并选择本项目所在仓库。
4. `Build Command` 填写：

```bash
pip install -r requirements.txt
```

5. `Start Command` 填写：

```bash
gunicorn app:app
```

6. 部署完成后，如果数据库中还没有演示数据，可以在 Render 的 Shell 中运行：

```bash
python seed_data.py
```

7. 访问公网地址：

```text
https://你的项目名.onrender.com/login
```

测试账号：

```text
管理员：admin / admin123
普通用户：student / student123
```

注意事项：

1. Render 免费服务可能会休眠，第一次打开页面可能较慢。
2. 当前系统使用 SQLite，适合课程设计原型和短期演示。
3. Render 免费环境的本地文件存储可能不是长期持久化存储，重新部署或重启后数据库文件可能需要重新初始化。
4. 如果要长期线上使用，建议将 SQLite 改为 PostgreSQL 或 MySQL。
5. 本项目的 `app.py` 会在启动时自动初始化基础数据表，但不会重复插入大量演示数据；演示账号和演示物品需要通过 `python seed_data.py` 导入。

## 测试账号

- 管理员：admin / admin123
- 普通用户：student / student123
- 其他普通用户：xiaolin、mingming、xiaoyu、haoran，密码均为 123456

## 功能说明

- 普通用户：注册登录、发布失物或招领信息、搜索筛选、查看详情、提交认领申请、查看我的发布和我的申请。
- 智能匹配：基于规则的轻量匹配算法，按类型互补、分类一致、关键词相似、地点相近、时间接近、描述重合计算匹配度。
- 管理员：查看统计看板、管理物品状态、归档信息、审核认领申请、查看用户发布数量。
- 加急寻物服务：用户可对自己发布的失物提交模拟加急申请，管理员审核通过后首页优先展示，并在智能匹配中增加排序权重。

## 加急模块测试路线

1. 使用 student / student123 登录。
2. 进入“我的发布”，选择一条自己发布的失物信息。
3. 点击“申请加急”，填写加急等级、加急原因和联系方式。
4. 提交后进入“我的加急申请”，查看“待审核”状态和模拟支付状态。
5. 退出后使用 admin / admin123 登录。
6. 进入“加急工单管理”，筛选或查看待审核工单。
7. 点击“通过”，系统会生成置顶到期时间。
8. 回到首页，确认通过且未过期的加急失物优先显示，并带有“加急寻物”“优先匹配中”标签。

## 项目结构

```text
campus_lost_found/
├── app.py
├── database.py
├── models.py
├── services.py
├── seed_data.py
├── requirements.txt
├── README.md
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── uploads/.gitkeep
├── templates/
└── docs/
```
