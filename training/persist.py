import os
import shutil
import time


def _targets(tag: str) -> list[str]:
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    name = f'{tag}-{stamp}.zip'
    out = []
    drive = '/content/drive/MyDrive'
    if os.path.isdir(drive):
        d = os.path.join(drive, 'pluco-runs')
        os.makedirs(d, exist_ok=True)
        out.append(os.path.join(d, name))
    kg = '/kaggle/working'
    if os.path.isdir(kg):
        out.append(os.path.join(kg, name))
    if not out:
        out.append(os.path.join('/tmp', name))
    return out


def persist_dir(src: str, tag: str) -> list[str]:
    """Zip src and copy it somewhere durable, one copy per available target.

    A Colab/T4 VM can be reclaimed at any moment, so artifacts are pushed off
    the machine as soon as a stage finishes instead of waiting for a final cell.
    Returns the paths written.
    """
    if not os.path.isdir(src):
        raise FileNotFoundError(src)
    written = []
    for dest in _targets(tag):
        if dest.endswith('.zip'):
            base = dest[:-4]
        else:
            base = dest
        path = shutil.make_archive(base, 'zip', src)
        written.append(path)
    return written


def persist_file(path: str, tag: str) -> list[str]:
    """Copy a single artifact off the machine alongside a zip of its folder."""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    written = []
    for dest in _targets(tag):
        folder = os.path.dirname(dest)
        os.makedirs(folder, exist_ok=True)
        target = os.path.join(folder, os.path.basename(path))
        shutil.copy2(path, target)
        written.append(target)
    return written
