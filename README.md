# DeepSeek 余额桌宠

一个漂浮在桌面的宠物小图标，左键单击即可查询 DeepSeek API 余额。

## 功能

- 桌面右下角常驻，始终置顶
- 左键单击 → 查询余额（仅显示金额）
- 左键按住拖动 → 移动位置
- 右键菜单 → 设置 API Key / 退出
- 余额气泡为半透明毛玻璃效果
- 不出现在任务栏

## 使用方法

1. 从 [Releases](../../releases) 下载 `DeepSeek余额桌宠.exe`
2. 运行，右键宠物 → **设置 API Key**
3. 输入你的 DeepSeek API Key（在 [platform.deepseek.com](https://platform.deepseek.com/api_keys) 获取）
4. 左键单击宠物查询余额

## 从源码运行

```bash
pip install -r requirements.txt
python deskpet.py
```

## 打包为 EXE

```bash
pip install pyinstaller
build_exe.bat
```

## 技术说明

- Python 3.10 + tkinter
- 图标使用 SVG 格式，通过 `svg.path` + PIL 纯 Python 渲染
- 余额查询使用 DeepSeek API: `GET https://api.deepseek.com/user/balance`
- 任务栏隐藏使用 `ITaskbarList::DeleteTab` COM 接口
