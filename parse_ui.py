import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')
try:
    tree = ET.parse('current_dump.xml')
    for n in tree.iter('node'):
        t = n.attrib.get('text', '')
        d = n.attrib.get('content-desc', '')
        b = n.attrib.get('bounds', '')
        c = n.attrib.get('class', '')
        f = n.attrib.get('focused', '')
        c_able = n.attrib.get('clickable', '')
        if t or d or c_able == 'true':
            print(f"{b} (clickable={c_able}, focused={f}): [{c}] text='{t}' desc='{d}'")
except Exception as e:
    print(e)
