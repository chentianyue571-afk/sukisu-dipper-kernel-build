#include <linux/cred.h>
#include <linux/mount.h>
#include <linux/namei.h>
#include <linux/susfs.h>
#include <linux/uaccess.h>
#include <linux/version.h>

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 0, 0)
#define susfs_access_ok(addr, size) access_ok(addr, size)
#else
#define susfs_access_ok(addr, size) access_ok(VERIFY_WRITE, addr, size)
#endif

#define KERNEL_SU_OPTION 0xDEADBEEF

#ifndef MNT_DETACH
#define MNT_DETACH 2
#endif

#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
extern int path_umount(struct path *path, int flags);
extern bool susfs_is_mnt_devname_ksu(struct path *path);

void ksu_try_umount(const char *mnt, bool check_mnt, int flags, uid_t uid)
{
    struct path path;

    (void)uid;

    if (kern_path(mnt, 0, &path))
        return;

    if (path.dentry != path.mnt->mnt_root ||
        (check_mnt && !susfs_is_mnt_devname_ksu(&path))) {
        path_put(&path);
        return;
    }

    path_umount(&path, flags);
}

void susfs_try_umount_all(uid_t uid)
{
    susfs_try_umount(uid);
    ksu_try_umount("/system", true, 0, uid);
    ksu_try_umount("/system_ext", true, 0, uid);
    ksu_try_umount("/vendor", true, 0, uid);
    ksu_try_umount("/product", true, 0, uid);
    ksu_try_umount("/odm", true, 0, uid);
    ksu_try_umount("/data/adb/modules", false, MNT_DETACH, uid);
    ksu_try_umount("/debug_ramdisk", true, MNT_DETACH, uid);
}
#endif

static void susfs_reply(unsigned long arg5, int error)
{
    if (arg5 && susfs_access_ok((void __user *)arg5, sizeof(error)))
        copy_to_user((void __user *)arg5, &error, sizeof(error));
}

int ksu_handle_susfs_prctl(int option, unsigned long cmd, unsigned long arg3,
                           unsigned long arg4, unsigned long arg5)
{
    int error = 0;

    if ((u32)option != KERNEL_SU_OPTION || current_uid().val != 0)
        return 0;

    switch (cmd) {
#ifdef CONFIG_KSU_SUSFS_SUS_PATH
    case CMD_SUSFS_ADD_SUS_PATH:
        error = susfs_add_sus_path((struct st_susfs_sus_path __user *)arg3);
        break;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
    case CMD_SUSFS_ADD_SUS_MOUNT:
        error = susfs_add_sus_mount((struct st_susfs_sus_mount __user *)arg3);
        break;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
    case CMD_SUSFS_ADD_SUS_KSTAT:
    case CMD_SUSFS_ADD_SUS_KSTAT_STATICALLY:
        error = susfs_add_sus_kstat((struct st_susfs_sus_kstat __user *)arg3);
        break;
    case CMD_SUSFS_UPDATE_SUS_KSTAT:
        error = susfs_update_sus_kstat((struct st_susfs_sus_kstat __user *)arg3);
        break;
#endif
#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
    case CMD_SUSFS_ADD_TRY_UMOUNT:
        error = susfs_add_try_umount((struct st_susfs_try_umount __user *)arg3);
        break;
    case CMD_SUSFS_RUN_UMOUNT_FOR_CURRENT_MNT_NS:
        susfs_try_umount(current_uid().val);
        break;
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
    case CMD_SUSFS_SET_UNAME:
        error = susfs_set_uname((struct st_susfs_uname __user *)arg3);
        break;
#endif
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
    case CMD_SUSFS_ENABLE_LOG:
        if (arg3 > 1) {
            error = -EINVAL;
        } else {
            susfs_set_log(arg3);
        }
        break;
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
    case CMD_SUSFS_SET_CMDLINE_OR_BOOTCONFIG:
        error = susfs_set_cmdline_or_bootconfig((char __user *)arg3);
        break;
#endif
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
    case CMD_SUSFS_ADD_OPEN_REDIRECT:
        error = susfs_add_open_redirect((struct st_susfs_open_redirect __user *)arg3);
        break;
#endif
    case CMD_SUSFS_SHOW_VERSION:
        error = copy_to_user((void __user *)arg3, SUSFS_VERSION,
                             sizeof(SUSFS_VERSION));
        break;
    case CMD_SUSFS_SHOW_VARIANT:
        error = copy_to_user((void __user *)arg3, SUSFS_VARIANT,
                             sizeof(SUSFS_VARIANT));
        break;
    case CMD_SUSFS_SHOW_ENABLED_FEATURES: {
        u64 features = 0;
#ifdef CONFIG_KSU_SUSFS_SUS_PATH
        features |= 1ULL << 0;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
        features |= 1ULL << 1;
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT
        features |= 1ULL << 2;
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT
        features |= 1ULL << 3;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
        features |= 1ULL << 4;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_OVERLAYFS
        features |= 1ULL << 5;
#endif
#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
        features |= 1ULL << 6;
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT
        features |= 1ULL << 7;
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
        features |= 1ULL << 8;
#endif
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
        features |= 1ULL << 9;
#endif
#ifdef CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS
        features |= 1ULL << 10;
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
        features |= 1ULL << 11;
#endif
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
        features |= 1ULL << 12;
#endif
#ifdef CONFIG_KSU_SUSFS_HAS_MAGIC_MOUNT
        features |= 1ULL << 14;
#endif
        error = copy_to_user((void __user *)arg3, &features, sizeof(features));
        break;
    }
    case CMD_SUSFS_SHOW_SUS_SU_WORKING_MODE:
    case CMD_SUSFS_IS_SUS_SU_READY:
    case CMD_SUSFS_SUS_SU:
        error = 1;
        break;
    default:
        return 0;
    }

    susfs_reply(arg5, error);
    return 1;
}
