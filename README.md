# MTH2HTML - QQ 聊天记录 MHT 转 HTML 工具

该工具用于将 QQ 聊天记录的 MHT 文件转换为 HTML 格式，并提取其中的资源（如图片、表情等）保存到指定目录。转换后的 HTML 会包含原始 MHT 内容，并且会更新其中的资源引用路径。

## ✨ 特性

- 支持多线程处理，提高处理速度。
- 自动提取和保存 MHT 文件中的资源（图片、表情等）。
- 将 HTML 中的内联样式转换为 CSS 类。
- 支持自定义输出目录和资源存放目录。
- 自动处理空白记录并插入提示文本。

## 📥 安装

确保你的环境已安装 Python 3.6+，并安装以下依赖：

```bash
pip install beautifulsoup4 tqdm
```

## 🛠️ 使用

### ⚙️ 参数

```
usage: mht2html.py [-h] [--dir DIR] [--work WORK] mht_path output_path

将 QQ 聊天记录的 MHT 文件转换为 HTML。

positional arguments:
  mht_path             MHT 文件路径
  output_path          输出的 HTML 文件路径

optional arguments:
  -h, --help           show this help message and exit
  --dir DIR            保存资源的目录（默认：images）
  --work WORK          使用的线程数（默认：4）
```

### 📝 示例

将 `example.mht` 文件转换为 `output.html`，并将资源保存到 `resources` 目录：

```bash
python mht_to_html.py example.mht output.html --dir resources
```

## 🤝 贡献

欢迎提交问题和 pull request！如有任何问题，欢迎通过 issue 向我反馈。
