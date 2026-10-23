"""核验发行包的真实资源、哈希、引用、归档路径与适配元数据。"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/iivv'


def check_links(path):
    text = path.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' in target or target.startswith('#'):
            continue
        target = target.split('#')[0]
        assert (path.parent / target).exists(), f'引用缺失：{path}: {target}'
    for target in re.findall(r'<img\s+src="([^"]+)"', text):
        assert (path.parent / target).is_file(), f'图片缺失：{path}: {target}'


def main():
    manifest = json.loads((SKILL / 'assets/manifest.json').read_text(encoding='utf-8'))
    ids = [r['id'] for r in manifest]
    assert len(ids) == len(set(ids)), '图片编号重复'
    hashes = []
    for row in manifest:
        data = (SKILL / row['path']).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        assert actual == row['sha256'] and len(data) == row['bytes'], row['id']
        assert row['source_page'].startswith('https://'), row['id']
        assert row['language'] in ['中文', '无字', '感叹号'], row['id']
        assert row['visual_review'].startswith('已目视'), row['id']
        hashes.append(actual)
    assert len(hashes) == len(set(hashes)), '重复图片字节'
    actual_paths = {p.relative_to(SKILL).as_posix() for p in (SKILL/'assets/memes').iterdir() if p.is_file()}
    assert actual_paths == {r['path'] for r in manifest}, '素材目录与清单存在差异'
    for path in ROOT.rglob('*.md'):
        if 'dist' not in path.parts: check_links(path)
    for name,adapted in [('iivv-v1.0.0.zip',False),('iivv-workbuddy-v1.0.0.zip',True)]:
        with zipfile.ZipFile(ROOT/'dist'/name) as z:
            assert z.testzip() is None
            names = set(z.namelist())
            assert 'iivv/SKILL.md' in names
            assert all(n.startswith('iivv/') and '..' not in PurePosixPath(n).parts for n in names)
            mf = 'references/manifest.json' if adapted else 'assets/manifest.json'
            for row in json.loads(z.read('iivv/'+mf)):
                assert hashlib.sha256(z.read('iivv/'+row['path'])).hexdigest() == row['sha256']
            body = z.read('iivv/SKILL.md').decode('utf-8')
            if adapted:
                assert all(k+':' in body.split('---')[1] for k in ['description_zh','description_en','version','author'])
                assert all(not n.startswith('iivv/assets/') for n in names)
            else:
                expected = { 'iivv/'+p.relative_to(SKILL).as_posix() for p in SKILL.rglob('*') if p.is_file() }
                assert names == expected
    patterns=(SKILL/'references/patterns.md').read_text(encoding='utf-8')
    nodes=re.findall(r'^\| ([LGYKОOHT]\d{2}) \|', patterns, re.M)
    assert len(nodes)==len(set(nodes))==60, f'梗节点：{len(nodes)}'
    sources=(SKILL/'references/sources.md').read_text(encoding='utf-8')
    for tag in re.findall(r'\[([^\]]+)\](?!\()',patterns):
        assert f'| {tag} |' in sources, f'来源标签缺失：{tag}'
    print(json.dumps({'结果':'通过','梗节点':len(nodes),'图片':len(manifest),'中文图片':sum(r['language']=='中文' for r in manifest),'无字或标点':sum(r['language']!='中文' for r in manifest),'验证':'本地引用、图像哈希与去重、素材集合、两个ZIP内容及路径、适配元数据、来源标签'},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
