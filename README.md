# MC开服 PC 版

手机版 MC开服 的电脑版：一键下载 Paper/Purpur 核心 → 创建/配置/运行 Minecraft 服务器。

## 下载
Releases → `MC-Fuwuqi-offline.zip`（含内置 JRE，解压后双击 MC-Fuwuqi.exe，无需安装 Java）

## 使用
1. ＋ 新建服务器 → 选核心和版本 → 创建（自动下载核心）
2. ▶ 启动（需要电脑装有 Java 17+，https://adoptium.net）
3. 控制台可输入命令（op / stop 等），「配置 server.properties」改设置
4. 服务器文件在 `~/MCFuwuqi/<服务器名>/`

## 构建
push 打 tag `v*` 或手动 workflow_dispatch → Actions 出 exe 传 Release
