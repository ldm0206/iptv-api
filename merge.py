import xml.etree.ElementTree as ET
from collections import defaultdict
import aiohttp
import asyncio
from datetime import datetime
import tarfile
from xml.dom import minidom
import re

urls = [
    "https://raw.githubusercontent.com/fanmingming/live/main/e.xml",
    "https://assets.livednow.com/epg.xml"
]


async def fetch_epg(url):
    connector = aiohttp.TCPConnector(limit=16, verify_ssl=False)
    async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
        async with session.get(url) as response:
            return await response.text(encoding='utf-8')


async def parse_epg(epg_content):
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
        channel_id = channel.get('id')
        display_name = channel.find('display-name').text
        channels[channel_id] = display_name

    for programme in root.findall('programme'):
        channel_id = programme.get('channel')
        programmes[channel_id].append(programme)

    return channels, programmes

def remove_duplicates(programmes):
    unique_programmes = defaultdict(list)
    for display_name, progs in programmes.items():
        seen = set()
        for prog in progs:
            title = prog.find('title').text
            if title not in seen:
                unique_programmes[display_name].append(prog)
                seen.add(title)
    return unique_programmes


def write_to_xml(channels, programmes, filename):
    current_time = datetime.now().strftime("%Y%m%d%H%M%S +0800")
    root = ET.Element('tv', attrib={'date': current_time})
    for channel_id, display_name in channels.items():
        channel_elem = ET.SubElement(root, 'channel', attrib={"id":channel_id})
        display_name_elem = ET.SubElement(channel_elem, 'display-name', attrib={"lang": "zh"})
        display_name_elem.text = display_name
        for prog in programmes[channel_id]:
            root.append(prog)

    # Beautify the XML output
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(reparsed.toprettyxml(" "))


def compress_to_tar_gz(input_filename, output_filename):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(input_filename, arcname="epg.xml")

async def main():
    tasks = [fetch_epg(url) for url in urls]
    epg_contents = await asyncio.gather(*tasks)

    all_channels = {}
    all_programmes = defaultdict(list)

    for epg_content in epg_contents:
        channels, programmes = await parse_epg(epg_content)
        for channel_id, display_name in channels.items():
            if channel_id not in all_channels and display_name not in all_channels:
                all_channels[channel_id] = display_name
                all_programmes[channel_id] = programmes[channel_id]
    write_to_xml(all_channels, remove_duplicates(all_programmes), 'output/epg.xml')
    compress_to_tar_gz('output/epg.xml', 'output/epg.tar.gz')

if __name__ == '__main__':
    asyncio.run(main())
