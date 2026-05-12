# data-example

此目录展示 `data/` 文件夹的结构和输出格式示例，方便你了解解析结果的预期格式。

```
data-example/
├── input/           # 存放 .docx 会议记录（放入你自己的文件）
├── output/          # 解析结果输出（.json）
└── README.md
```

实际使用时，程序会在 `data/` 目录下自动创建 `input/`、`output/` 子目录和 `meeting_agent.db` 数据库文件。

> `data/` 目录已加入 `.gitignore`，不会上传到 Git 仓库。实际使用时程序会自动创建所需目录和文件。
