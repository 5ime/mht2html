import re
import os
import base64
import argparse
from tqdm import tqdm
from bs4 import BeautifulSoup
from typing import Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

CONTENT_TYPE_MAP = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif"
}

def parse_headers(headers_str: str) -> Dict[str, str]:
    """解析HTTP头部字符串为字典"""
    headers = {}
    for line in headers_str.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    return headers

def save_resource(
    content_location: str,
    content_type: str,
    data: str,
    encoding: str,
    resource_dir: str,
    progress_callback=None
) -> Optional[Tuple[str, str]]:
    """保存资源文件到指定目录"""
    try:
        # 提取原始文件名并去除已有扩展名
        original_name = os.path.basename(content_location)
        base_name = os.path.splitext(original_name)[0]
        
        # 获取正确扩展名
        extension = CONTENT_TYPE_MAP.get(
            content_type, 
            content_type.split("/")[-1].split("+")[-1]
        )

        os.makedirs(resource_dir, exist_ok=True)
        filename = f"{base_name}.{extension}"
        file_path = os.path.join(resource_dir, filename)

        # 处理不同编码格式
        content = base64.b64decode(data) if encoding == "base64" else data.encode("utf-8")

        with open(file_path, "wb") as f:
            f.write(content)

        if progress_callback:
            progress_callback(1)  # 每保存一个资源，更新进度条
        
        return (content_location, file_path)
    except Exception as e:
        print(f"保存资源失败 {content_location}: {str(e)}")
        return None
    
class MHTProcessor:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def empty_msg(self, soup: BeautifulSoup) -> None:
        """处理空白记录"""
        for div in soup.find_all("div", style="padding-left:20px;"):
            # 先排除有图像的消息
            if div.find("img"):
                continue

            if not div.get_text(strip=True):
                new_div = soup.new_tag("div", **{"style": "padding-left:20px;"})
                new_font = soup.new_tag("font", style="font-size:10pt;font-family:'宋体','MS Sans Serif',sans-serif;", color="000000")
                new_font.string = "[不支持导出的消息类型]"

                new_div.append(new_font)
                div.insert_before(new_div)
                div.decompose()

        print("空白记录已成功替换为提示文本。")

    def process_styles(self, soup: BeautifulSoup) -> str:
        """将内联样式转换为 CSS 类"""
        style_map = {}
        css_rules = []
        counter = 1
        
        for element in soup.find_all(style=True):
            if not (original_style := element.get("style", "").strip()):
                continue

            if original_style not in style_map:
                class_name = f"i-style-{counter}"
                style_map[original_style] = class_name
                css_rules.append(f".{class_name} {{ {original_style} }}")
                counter += 1

            element["class"] = element.get("class", []) + [style_map[original_style]]
            del element["style"]
        print("内联样式已成功转换为 CSS 类。")

        return "\n".join(css_rules)

    def update_references(
        self,
        soup: BeautifulSoup,
        resource_map: Dict[str, str],
        output_path: str
    ) -> None:
        """更新 HTML 资源引用路径"""
        for tag in soup.find_all(["img", "link", "script"]):
            attr = "src" if tag.name == "img" else "href"
            if resource_path := resource_map.get(tag.get(attr, "")):
                relative_path = os.path.relpath(
                    resource_path,
                    start=os.path.dirname(output_path)
                )
                tag[attr] = relative_path
        print("HTML 中的资源引用路径已成功更新。")

    def process(
        self,
        mht_path: str,
        output_path: str,
        resource_dir: str = "images"
    ) -> bool:
        """主处理流程"""
        try:
            print(f"正在读取 MHT 文件：{mht_path}...")
            with open(mht_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析 MHT 结构
            if not (boundary_match := re.search(r'boundary="([^"]+)"', content)):
                raise ValueError("无效的 MHT 文件格式：缺少 boundary 声明")
            
            boundary = boundary_match.group(1)
            parts = re.split(rf"--{boundary}(?:--)?\n", content)

            html_part = next((p for p in parts if "Content-Type: text/html" in p), None)
            if not html_part:
                raise ValueError("MHT 文件中缺少 HTML 内容")

            if not (html_match := re.search(r"(?:\n\n|\r\n\r\n)(.*?)(?=\n--|$)", html_part, re.DOTALL)):
                raise ValueError("HTML 内容解析失败")
            
            soup = BeautifulSoup(html_match.group(1).strip(), "html.parser")

            self.empty_msg(soup)

            css_content = self.process_styles(soup)

            futures = []
            resource_map = {}
            resource_dir = os.path.join(os.path.dirname(output_path), resource_dir)

            total_resources = 0
            for part in parts:
                if "Content-Location:" not in part:
                    continue
                headers_str, _, body = part.partition("\n\n")
                headers = parse_headers(headers_str)
                if headers.get("content-location"):
                    total_resources += 1  # 统计资源数量

            with tqdm(total=total_resources, desc="资源转存进度", ncols=100) as progress_bar:
                for part in parts:
                    if "Content-Location:" not in part:
                        continue

                    headers_str, _, body = part.partition("\n\n")
                    headers = parse_headers(headers_str)
                    content_location = headers.get("content-location")
                    content_type = headers.get("content-type", "").split(";")[0]
                    encoding = headers.get("content-transfer-encoding", "7bit")

                    if content_type.startswith("text/html"):
                        continue

                    futures.append(
                        self.executor.submit(
                            save_resource,
                            content_location,
                            content_type,
                            body.strip(),
                            encoding,
                            resource_dir,
                            progress_bar.update
                        )
                    )

                for future in as_completed(futures):
                    if result := future.result():
                        resource_map[result[0]] = result[1]

            self.update_references(soup, resource_map, output_path)

            if css_content:
                style_tag = soup.new_tag("style", type="text/css")
                style_tag.string = css_content
                if soup.head:
                    soup.head.append(style_tag)
                else:
                    soup.html.insert(0, soup.new_tag("head")).append(style_tag)

            with open(output_path, "w", encoding="utf-8") as f:
                # f.write(soup.prettify())
                f.write(str(soup))

            print(f"转换成功: {output_path}")
            return True

        except Exception as e:
            print(f"处理失败: {str(e)}")
            return False
        finally:
            self.executor.shutdown(wait=True)

def main():
    parser = argparse.ArgumentParser(description="将 QQ 聊天记录的 MHT 文件转换为 HTML。")
    parser.add_argument("mht_path", help="MHT 文件路径")
    parser.add_argument("output_path", help="输出的 HTML 文件路径")
    parser.add_argument(
        "--dir", 
        default="images", 
        help="保存资源的目录（默认：images）"
    )
    parser.add_argument(
        "--work", 
        type=int, 
        default=4, 
        help="使用的线程数（默认：4）"
    )
    
    args = parser.parse_args()

    processor = MHTProcessor(max_workers=args.work)
    processor.process(args.mht_path, args.output_path, args.dir)

if __name__ == "__main__":
    main()