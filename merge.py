import xml.etree.ElementTree as ET
from collections import defaultdict
import aiohttp
import asyncio
from datetime import datetime
import gzip
import shutil
from xml.dom import minidom
import re
from opencc import OpenCC

urls = [
    "http://epg.51zmt.top:8000/e.xml",
    "https://e.erw.cc/e.xml",
    "https://raw.githubusercontent.com/fanmingming/live/main/e.xml",
    "https://assets.livednow.com/epg.xml"
]



def transform2_zh_hans(string):
    cc = OpenCC("t2s")
    new_str = cc.convert(string)
    return new_str

async def fetch_epg(url):
    connector = aiohttp.TCPConnector(limit=16, ssl=False)
    async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
        async with session.get(url) as response:
            return await response.text(encoding='utf-8')


def parse_epg(epg_content):
    try:
        parser = ET.XMLParser(encoding='UTF-8')
        root = ET.fromstring(epg_content, parser=parser)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        print(f"Problematic content: {epg_content[:500]}")  
        return {}, defaultdict(list)

    channels = {}
    programmes = defaultdict(list)

    for channel in root.findall('channel'):
        channel_id = transform2_zh_hans(channel.get('id'))
        display_name = transform2_zh_hans(channel.find('display-name').text)
        channels[channel_id] = display_name

    for programme in root.findall('programme'):
        channel_id = transform2_zh_hans(programme.get('channel'))
        channel_start = datetime.strptime(
            re.sub(r'\s+', '', programme.get('start')), "%Y%m%d%H%M%S%z")
        channel_stop = datetime.strptime(
            re.sub(r'\s+', '', programme.get('stop')), "%Y%m%d%H%M%S%z")
        channel_text = transform2_zh_hans(programme.find('title').text)
        channel_elem = ET.SubElement(
            root, 'programme', attrib={"channel": channel_id, "start": channel_start.strftime("%Y%m%d%H%M%S +0800"), "stop": channel_stop.strftime("%Y%m%d%H%M%S +0800")})
        channel_elem_s = ET.SubElement(
            channel_elem, 'title', attrib={"lang": "zh"})
        channel_elem_s.text = channel_text
        programmes[channel_id].append(channel_elem)

    return channels, programmes

def write_to_xml(channels, programmes, filename):
    current_time = datetime.now().strftime("%Y%m%d%H%M%S +0800")
    root = ET.Element('tv', attrib={'date': current_time})
    for channel_id in channels:
        channel_elem = ET.SubElement(root, 'channel', attrib={"id":channel_id})
        display_name_elem = ET.SubElement(channel_elem, 'display-name', attrib={"lang": "zh"})
        display_name_elem.text = channel_id
        for prog in programmes[channel_id]:
            prog.set('channel', channel_id)  # 设置 programme 的 channel 属性
            root.append(prog)

    # Beautify the XML output
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(reparsed.toprettyxml(indent='\t', newl='\n'))


def compress_to_gz(input_filename, output_filename):
    with open(input_filename, 'rb') as f_in:
        with gzip.open(output_filename, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

async def main():
    tasks = [fetch_epg(url) for url in urls]
    epg_contents = await asyncio.gather(*tasks)
    all_channels = set()
    all_channels_verify = set()
    all_programmes = defaultdict(list)

    for epg_content in epg_contents:
        channels, programmes = parse_epg(epg_content)
        for channel_id, display_name in channels.items():
            display_name = display_name.replace(' ', '')
            if channel_id not in all_channels_verify and display_name not in all_channels_verify:
                if not channel_id.isdigit():
                    all_channels_verify.add(channel_id)
                all_channels.add(display_name)
                all_channels_verify.add(display_name)
                all_programmes[display_name] = programmes[channel_id]
    write_to_xml(all_channels, all_programmes, 'output/epg.xml')
    compress_to_gz('output/epg.xml', 'output/epg.gz')

if __name__ == '__main__':
    asyncio.run(main())
