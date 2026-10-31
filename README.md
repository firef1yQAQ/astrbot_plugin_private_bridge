# 私聊互通 (private_bridge)

AstrBot 的每个私聊会话互相隔离，这个插件让 bot 知道**其他私聊好友**最近说了什么。

## 行为

- 记录每个私聊联系人最近 20 条消息（内存 + JSON 落盘）
- 处理私聊请求时，把其他联系人的最近 6 条作为背景注入 system prompt
- 只注入给私聊；群聊不受影响
- 提示词要求“被问到才说，不主动泄露”

## 数据

`data/plugin_data/astrbot_plugin_private_bridge/chats.json`，可随时删除重置。

## 安装

放进 `data/plugins/`，重启 AstrBot。适用于 AstrBot >= 4.0.0。
