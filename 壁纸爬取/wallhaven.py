import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import re
import time
from tqdm import tqdm
import os


username = os.getenv("download_wallpaper_username")
password = os.getenv("download_wallpaper_password")
print(f"用户名: {username}, 密码: {password}")
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

def wallhaven_login(username, password):
    login_url = "https://wallhaven.cc/login"
    post_url = "https://wallhaven.cc/auth/login"

    session = requests.Session()
    
    # Optimize session for better performance
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=3
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    resp = session.get(login_url)
    soup = BeautifulSoup(resp.text, "html.parser")
    token_input = soup.find("input", {"name": "_token"})
    token = token_input['value'] if token_input else ""
    print(f"获取到的_token: {token}")

    payload = {
        "_token": token,
        "username": username,
        "password": password,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
        "Referer": login_url,
        "Origin": "https://wallhaven.cc",
    }

    login_response = session.post(post_url, data=payload, headers=headers, allow_redirects=True)
    print("登录响应地址:", login_response.url)

    if login_response.url.startswith("https://wallhaven.cc/user/"):
        print("登录成功！")
        return session
    else:
        print("登录失败，可能是用户名或密码错误")
        return None

def checkHttps(response):
    soup = BeautifulSoup(response.content, "html.parser")
    title_tag = soup.find("title")
    if title_tag and "404" in title_tag.text:
        return False
    return True

def downLoad(session, image_id, save_dir):
    prefix = image_id[:2]
    base_url = f"https://w.wallhaven.cc/full/{prefix}/wallhaven-{image_id}"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    for ext in ['jpg', 'png']:
        url = f"{base_url}.{ext}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = session.get(url, headers=headers, stream=True)
        if checkHttps(response):
            total_size = int(response.headers.get('content-length', 0))
            filename = os.path.join(save_dir, f"wallhaven-{image_id}.{ext}")
            if os.path.exists(filename):
                print(f"{filename} 已存在，跳过下载")
                return
            
            # Create more informative progress bar description
            file_size_mb = total_size / (1024 * 1024) if total_size > 0 else 0
            desc = f"📥 {image_id}.{ext} ({file_size_mb:.1f}MB)"
            
            with open(filename, 'wb') as f, tqdm(
                desc=desc,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]',
            ) as bar:
                for data in response.iter_content(chunk_size=65536):  # Increased chunk size to 64KB
                    if data:  # Only write non-empty chunks
                        size = f.write(data)
                        bar.update(size)
            print(f"✅ 已成功下载: {os.path.basename(filename)}")
            return
    print(f"❌ 图片 {image_id} 下载失败（jpg和png均尝试失败）")

def GetHtmlPack(session, page, target):
    # search_url = f"https://wallhaven.cc/search?q={target}&categories=001&purity=100&sorting=relevance&order=desc&ai_art_filter=1&page={page}"
    search_url = f"https://wallhaven.cc/search?q={target}&categories=001&purity=001&atleast=2560x1440&ratios=landscape&sorting=favorites&order=desc&ai_art_filter=1&page={page}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = session.get(search_url, headers=headers)
    if response.status_code != 200:
        print(f"请求失败，状态码：{response.status_code}")
        return
    
    soup = BeautifulSoup(response.content, 'html.parser')
    preview_links = soup.find_all("a", attrs={"class": "preview", "target": "_blank"})

    pattern = re.compile(r'https://wallhaven.cc/w/([0-9a-z]{6})')
    
    # Collect all image IDs first
    image_ids = []
    for a_tag in preview_links:
        href = a_tag.get('href', '')
        match = pattern.search(href)
        if match:
            image_ids.append(match.group(1))
    
    print(f"🔍 找到 {len(image_ids)} 张图片，开始下载...")

    for i, image_id in enumerate(image_ids, 1):
        print(f"\n📄 [{i}/{len(image_ids)}] 准备下载图片: {image_id}")
        downLoad(session, image_id, save_dir=r"/Users/gmh/code/我的练习代码/壁纸爬取/壁纸文件")
        time.sleep(0.5)  # Reduced delay from 1.2s to 0.5s for faster overall processing
    
    print(f"🎉 批次下载完成！共处理 {len(image_ids)} 张图片")

if __name__ == '__main__':
    if not username or not password:
        print("请设置环境变量 download_wallpaper_username 和 download_wallpaper_password")
        sys.exit(1)
    session = wallhaven_login(username, password)
    if session:
        GetHtmlPack(session, 10, 'model')
