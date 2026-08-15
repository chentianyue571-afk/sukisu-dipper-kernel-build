#!/usr/bin/env python3

import argparse
from pathlib import Path


SKIPPED_HUNKS = {
    "@@ -954,7 +1053,17 @@ vfs_kern_mount(struct file_system_type *type, int flags, const char *name, void\n",
    "@@ -1009,7 +1127,52 @@ static struct mount *clone_mnt(struct mount *old, struct dentry *root,\n",
}


def prepare_patch(source_path: Path, output_path: Path) -> None:
    lines = source_path.read_text().splitlines(keepends=True)
    output = []
    skipped = set()
    index = 0

    while index < len(lines):
        line = lines[index]
        if line in SKIPPED_HUNKS:
            skipped.add(line)
            index += 1
            while index < len(lines):
                if lines[index].startswith("@@ ") or lines[index].startswith("diff --git "):
                    break
                index += 1
            continue
        output.append(line)
        index += 1

    if skipped != SKIPPED_HUNKS:
        missing = sorted(header.strip() for header in SKIPPED_HUNKS - skipped)
        raise SystemExit(f"SUSFS patch hunk headers changed: {missing}")

    output_path.write_text("".join(output))


def replace_once(path: Path, anchor: str, replacement: str) -> None:
    source = path.read_text()
    count = source.count(anchor)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}")
    path.write_text(source.replace(anchor, replacement, 1))


def patch_namespace(kernel_root: Path) -> None:
    path = kernel_root / "fs/namespace.c"

    anchor = '\tmnt = alloc_vfsmnt(fc->source ?: "none");\n'
    replacement = '''#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
\tif (unlikely(susfs_is_current_ksu_domain()))
\t\tmnt = alloc_vfsmnt(fc->source ?: "none", true, 0);
\telse
\t\tmnt = alloc_vfsmnt(fc->source ?: "none", false, 0);
#else
\tmnt = alloc_vfsmnt(fc->source ?: "none");
#endif
'''
    replace_once(path, anchor, replacement)

    anchor = '''\tstruct mount *mnt;
\tint err;

\tmnt = alloc_vfsmnt(old->mnt_devname);
'''
    replacement = '''\tstruct mount *mnt;
\tint err;

#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
\tbool is_current_ksu_domain = susfs_is_current_ksu_domain();
\tbool is_current_zygote_domain = susfs_is_current_zygote_domain();

\tif (unlikely(is_current_ksu_domain)) {
\t\tif (!(flag & CL_COPY_MNT_NS)) {
\t\t\tmnt = alloc_vfsmnt(old->mnt_devname, true, 0);
\t\t} else {
\t\t\tmnt = alloc_vfsmnt(old->mnt_devname, true, old->mnt_id);
\t\t\tif (mnt)
\t\t\t\tmnt->mnt.susfs_mnt_id_backup = DEFAULT_SUS_MNT_ID_FOR_KSU_PROC_UNSHARE;
\t\t}
\t} else if (likely(is_current_zygote_domain) &&
\t\t   old->mnt_id >= DEFAULT_SUS_MNT_ID) {
\t\tmnt = alloc_vfsmnt(old->mnt_devname, true, 0);
\t} else if ((flag & CL_COPY_MNT_NS) &&
\t\t   old->mnt_id >= DEFAULT_SUS_MNT_ID) {
\t\tmnt = alloc_vfsmnt(old->mnt_devname, true, 0);
\t} else {
\t\tmnt = alloc_vfsmnt(old->mnt_devname, false, 0);
\t}
#else
\tmnt = alloc_vfsmnt(old->mnt_devname);
#endif
'''
    replace_once(path, anchor, replacement)


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("source", type=Path)
    prepare.add_argument("output", type=Path)

    namespace = subparsers.add_parser("patch-namespace")
    namespace.add_argument("kernel_root", type=Path)

    args = parser.parse_args()
    if args.command == "prepare":
        prepare_patch(args.source, args.output)
    else:
        patch_namespace(args.kernel_root)


if __name__ == "__main__":
    main()
