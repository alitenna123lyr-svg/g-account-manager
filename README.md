# G-Account Manager

[English](#english) | [中文](#中文)
---
<img width="2560" height="1504" alt="image" src="https://github.com/user-attachments/assets/75128071-fcf2-490c-b750-5382629d2826" />


---

## English

A desktop application for managing multiple accounts and generating TOTP 2FA codes. Built with PyQt6.

### Features

#### Core Functions
- **TOTP 2FA Code Generation** - Auto-refresh every 30 seconds with countdown timer
- **Network Time Sync** - Uses internet time for accurate code generation
- **Account Management** - Add, edit, delete accounts with full information storage
- **Click to Copy** - Click any cell to copy content with toast notification

#### Organization
- **Group Management** - Create custom groups with color labels (8 colors available)
- **Drag & Drop Sorting** - Reorder groups by dragging
- **Filter by Group** - View all accounts, ungrouped, or specific groups
- **Batch Operations** - Select multiple accounts for bulk actions

#### Data Safety
- **Trash Bin** - Deleted accounts go to trash, can be restored
- **Auto Backup** - Creates timestamped backups on every operation
- **Undo Support** - Undo accidental deletions

#### Other Features
- **Duplicate Detection** - Highlights duplicate accounts in yellow
- **One-click Deduplication** - Remove all duplicates keeping unique accounts
- **File Import** - Import accounts from text files with auto separator detection
- **Bilingual UI** - Switch between English and Chinese

### Installation

```bash
# Clone the repository
git clone https://github.com/alitenna123lyr-svg/g-account-manager.git
cd g-account-manager

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

### Requirements

- Python 3.8+
- PyQt6
- pyotp

### Usage

#### Import Accounts

Prepare a text file with accounts in this format:
```
email@example.com----password----backup@email.com----2FA_SECRET_KEY
```

Supported separators (auto-detected):
- `----` (4 dashes)
- `---` (3 dashes)
- `--` (2 dashes)
- `\t` (tab)
- `,` (comma)

#### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Click cell | Copy content |
| Delete/Backspace | Delete selected account |

### Security Notes

- Account data is stored locally in `2fa_data.json`
- Data file is excluded from git by default
- Never commit sensitive account information to public repositories
- Backups are stored in `backups/` folder

### License

MIT License - see [LICENSE](LICENSE)

---

## 中文

一个用于管理多账户和生成 TOTP 2FA 验证码的桌面应用。基于 PyQt6 构建。

### 功能特性

#### 核心功能
- **TOTP 验证码生成** - 每30秒自动刷新，带倒计时显示
- **网络时间同步** - 使用网络时间确保验证码准确
- **账户管理** - 添加、编辑、删除账户，完整信息存储
- **点击复制** - 点击任意单元格复制内容，带提示通知

#### 分组管理
- **自定义分组** - 创建带颜色标签的分组（8种颜色可选）
- **拖拽排序** - 拖拽调整分组顺序
- **分组筛选** - 查看全部账户、未分组或特定分组
- **批量操作** - 多选账户进行批量处理

#### 数据安全
- **回收站** - 删除的账户进入回收站，可恢复
- **自动备份** - 每次操作自动创建带时间戳的备份
- **撤销功能** - 支持撤销误删除操作

#### 其他功能
- **重复检测** - 黄色高亮显示重复账户
- **一键去重** - 删除所有重复项，只保留唯一账户
- **文件导入** - 从文本文件导入，自动检测分隔符
- **双语界面** - 中英文切换

### 安装

```bash
# 克隆仓库
git clone https://github.com/alitenna123lyr-svg/g-account-manager.git
cd g-account-manager

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 环境要求

- Python 3.8+
- PyQt6
- pyotp

### 使用说明

#### 导入账户

准备一个文本文件，格式如下：
```
邮箱@example.com----密码----辅助邮箱@email.com----2FA密钥
```

支持的分隔符（自动检测）：
- `----`（4个短横线）
- `---`（3个短横线）
- `--`（2个短横线）
- `\t`（制表符）
- `,`（逗号）

#### 快捷键

| 按键 | 操作 |
|------|------|
| 点击单元格 | 复制内容 |
| Delete/Backspace | 删除选中账户 |

### 安全说明

- 账户数据保存在本地 `2fa_data.json` 文件中
- 数据文件默认被 git 忽略
- 请勿将敏感账户信息提交到公开仓库
- 备份文件保存在 `backups/` 文件夹

### 许可证

MIT License - 详见 [LICENSE](LICENSE)
