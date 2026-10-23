"""构建标准包、WorkBuddy 适配包和单文件提示词。仅写本仓库 dist 及文档。"""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/iivv'
VERSION = '1.0.0'


def source_files():
    return {p.relative_to(SKILL).as_posix(): p.read_bytes()
            for p in sorted(SKILL.rglob('*')) if p.is_file()}


def archive(path, files):
    # 固定时间与排序，让同一源文件得到可复现的压缩包。
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo('iivv/' + name, (2026, 10, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)


def main():
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    standard = source_files()
    archive(dist / f'iivv-v{VERSION}.zip', standard)
    adapted = {}
    for name, data in standard.items():
        target = name.replace('assets/memes/', 'references/images/').replace('assets/manifest.json', 'references/manifest.json')
        if name.endswith(('.md', '.json', '.yaml')):
            value = data.decode('utf-8')
            # 只替换相对路径；固定发布图片地址始终指向标准仓库资源。
            if name == 'assets/manifest.json':
                rows = json.loads(value)
                for row in rows:
                    row['path'] = row['path'].replace('assets/memes/', 'references/images/')
                value = json.dumps(rows, ensure_ascii=False, indent=2) + '\n'
            else:
                value = value.replace('](../assets/memes/', '](images/')
                value = value.replace('`assets/memes/', '`references/images/')
                value = value.replace('](../assets/manifest.json)', '](manifest.json)')
                value = value.replace('](assets/manifest.json)', '](references/manifest.json)')
            if name == 'SKILL.md':
                _, _, body = value.split('---', 2)
                value = ('---\nname: iivv\ndisplay_name: iivv 咒回接梗\n'
                         'description: 中文咒术回战接梗、情境改写和漫画表情包。\n'
                         'description_zh: 会接梗，也能办事的中文咒回搞怪助理。\n'
                         'description_en: Chinese Jujutsu Kaisen meme replies and reaction images.\n'
                         f'version: {VERSION}\nauthor: youngiry\nlicense: MIT\n---\n'
                         + body.lstrip()
                         + '\n资源入口：@references/callbacks.md、@references/patterns.md、@references/reactions.md、@references/sources.md。按当前场景读取对应文件。\n')
            data = value.encode('utf-8')
        adapted[target] = data
    archive(dist / f'iivv-workbuddy-v{VERSION}.zip', adapted)
    chunks = ['# iivv 通用提示词\n\n把本文件内容放入角色指令，或在聊天里交给助理读取并启用。默认中文、标准浓度、图片自动。图片使用固定版本地址，展示方式取决于宿主。\n']
    _, _, body = (SKILL / 'SKILL.md').read_text(encoding='utf-8').split('---', 2)
    chunks.append(body.strip())
    for name in ['callbacks.md', 'patterns.md', 'reactions.md']:
        chunks.append((SKILL / 'references' / name).read_text(encoding='utf-8'))
    prompt = '\n\n'.join(chunks) + '\n'
    for name in ['callbacks.md', 'patterns.md', 'reactions.md', 'sources.md']:
        remote = f'https://github.com/youngiry/iivv/blob/v1.0.0/skills/iivv/references/{name}'
        prompt = prompt.replace(f'](references/{name})', f']({remote})').replace(f']({name})', f']({remote})')
    rows = json.loads((SKILL / 'assets/manifest.json').read_text(encoding='utf-8'))
    for row in rows:
        prompt = prompt.replace(f'](../{row["path"]})', f']({row["remote_url"]})')
    prompt = prompt.replace('](../assets/manifest.json)', '](https://github.com/youngiry/iivv/blob/v1.0.0/skills/iivv/assets/manifest.json)')
    prompt = prompt.replace('路径以本技能所在目录为根。', '当前使用单文件提示词；素材采用下方固定版本远程地址。完整安装时路径以技能目录为根。')
    (ROOT / 'docs/通用提示词.md').write_text(prompt, encoding='utf-8')
    (dist / f'iivv-prompt-v{VERSION}.md').write_text(prompt, encoding='utf-8')
    sums = []
    for name in [f'iivv-v{VERSION}.zip', f'iivv-workbuddy-v{VERSION}.zip', f'iivv-prompt-v{VERSION}.md']:
        sums.append(f'{hashlib.sha256((dist/name).read_bytes()).hexdigest()}  {name}')
    (dist / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n', encoding='utf-8')
    print(json.dumps({'版本': VERSION, '标准包文件数': len(standard), '适配包文件数': len(adapted), '图片数': len(rows)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
