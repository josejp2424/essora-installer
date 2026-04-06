#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Copyright (C) 2026 Essora Linux
# Essora Installer - Backend (Devuan/OpenRC, no systemd)
# Autor: josejp2424

import json
import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any, List, Tuple

LogFn = Callable[[str], None]
ROOT_LABEL = "essora"


def detect_de_label() -> str:
    """Read /home/essora/.xsession and return a label based on the DE found."""
    xsession = "/home/essora/.xsession"
    try:
        if os.path.isfile(xsession):
            content = open(xsession, "r", encoding="utf-8", errors="ignore").read()
            if "jwm" in content:
                return "essora-jwm"
            if "openbox-session" in content or "openbox" in content:
                return "essora-openbox"
            if "startkde" in content or "startplasma" in content:
                return "essora-kde"
            if "startlxde" in content or "lxde" in content:
                return "essora-lxde"
    except Exception:
        pass
    return "essora"

# Paths belonging to the live environment that must NOT be copied to the installed disk
_LIVE_RSYNC_EXCLUDES = [
    "/dev/*",
    "/proc/*",
    "/sys/*",
    "/run/*",
    "/tmp/*",
    "/mnt/*",
    "/media/*",
    "/lost+found",
    # live-boot / live-config overlays
    "/lib/live/mount/*",
    "/lib/live/overlay/*",
    "/lib/live/image/*",
    "/lib/live/rootfs/*",
    "/run/live/*",
    # /lib -> /usr/lib symlink on some systems
    "/usr/lib/live/mount/*",
    "/usr/lib/live/overlay/*",
    # dynamic files regenerated on the installed system
    "/etc/fstab",
    "/etc/mtab",
    "/boot/grub/grub.cfg",
    "/boot/grub/menu.lst",
    "/boot/grub/device.map",
    "/var/lib/dbus/machine-id",
    "/etc/machine-id",
    "/etc/udev/rules.d/70-persistent-cd.rules",
    "/etc/udev/rules.d/70-persistent-net.rules",
    "/home/*/.gvfs",
    "/mnt/target/*",
]

# Live directories and files with no purpose on the installed system
_LIVE_RESIDUE_PATHS = [
    "lib/live",
    "usr/lib/live",
    "etc/live",
    "etc/profile.d/zz-live-config_xinit.sh",
    "etc/profile.d/zz-live-config_sysvinit.sh",
]

# init.d scripts belonging to the live environment — must be disabled/removed
_LIVE_INIT_SCRIPTS = [
    "live-config",
    "live-tools",
    "live-boot",
    "live-config-getty",
    "live-config-sysvinit",
    "live-config-upstart",
    "live-network",
    "live-swap",
]

_DM_AUTOLOGIN_RULES: List[Dict[str, Any]] = [
    {
        "cfg": "etc/lightdm/lightdm.conf",
        "pattern": r"^(autologin)",
        "replace": r"#\1",
    },
    {
        "cfg": "etc/lxdm/lxdm.conf",
        "pattern": r"^(autologin\s*=)",
        "replace": r"#\1",
    },
    {
        "cfg": "etc/gdm/gdm.conf",
        "pattern": r"^(AutomaticLogin)",
        "replace": r"#\1",
    },
    {
        "cfg": "etc/gdm3/daemon.conf",
        "pattern": r"^(AutomaticLogin)",
        "replace": r"#\1",
    },
    {
        "cfg": "etc/sddm.conf",
        "pattern": r"^(User\s*=)",
        "replace": r"#\1",
    },
]


@dataclass
class InstallPlan:
    # particiones
    root_part: str
    efi_part: Optional[str]
    format_root: bool
    root_fstype: str          

    # system
    timezone: str

    # usuario
    hostname: str
    username: str
    password: str

    # root
    root_password: str
    lock_root: bool

    # teclado
    kb_layout: str
    kb_model: str
    kb_variant: str
    kb_options: str

    # bootloader
    install_grub: bool
    grub_disk: str
    uefi: bool

    # separate /home partition 
    home_part: Optional[str] = field(default=None)
    format_home: bool = field(default=False)
    home_fstype: str = field(default="ext4")

    # swap partition (used in whole-disk mode)
    swap_part: Optional[str] = field(default=None)
    format_swap: bool = field(default=False)

    # display manager
    slim_autologin: bool = field(default=True)




def is_root() -> bool:
    return os.geteuid() == 0


def run(cmd: str, log: LogFn, check: bool = True,
        env: Optional[Dict[str, str]] = None) -> str:
    log(f"$ {cmd}")
    p = subprocess.run(
        cmd, shell=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
    )
    out = p.stdout or ""
    for line in out.splitlines():
        log(line)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {cmd}")
    return out


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def detach_mounts(target: str, log: LogFn):
    run(f"umount -R {shlex.quote(target)}", log, check=False)


def query_blkid(dev: str) -> Tuple[str, str]:
    uuid = subprocess.check_output(
        ["blkid", "-s", "UUID", "-o", "value", dev], text=True
    ).strip()
    fstype = subprocess.check_output(
        ["blkid", "-s", "TYPE", "-o", "value", dev], text=True
    ).strip()
    return uuid, fstype

def generate_fstab(
    root_mount: str,
    root_dev: str,
    efi_dev: Optional[str],
    home_dev: Optional[str],
    log: LogFn,
    swap_dev: Optional[str] = None,
):
    ensure_dir(os.path.join(root_mount, "etc"))
    root_uuid, root_type = query_blkid(root_dev)

    lines = [
        "# /etc/fstab - generated by essora-installer\n",
        f"UUID={root_uuid}  /         {root_type}  defaults,relatime  0  1\n",
    ]

    if efi_dev:
        efi_uuid, efi_type = query_blkid(efi_dev)
        lines.append(
            f"UUID={efi_uuid}  /boot/efi  {efi_type}  umask=0077,nofail  0  0\n"
        )

    if home_dev:
        home_uuid, home_type = query_blkid(home_dev)
        lines.append(
            f"UUID={home_uuid}  /home  {home_type}  defaults,relatime  0  2\n"
        )

    if swap_dev:
        try:
            swap_uuid = subprocess.check_output(
                ["blkid", "-s", "UUID", "-o", "value", swap_dev], text=True
            ).strip()
            if swap_uuid:
                lines.append(f"UUID={swap_uuid}  none  swap  sw  0  0\n")
        except Exception:
            lines.append(f"{swap_dev}  none  swap  sw  0  0\n")

    fstab_path = os.path.join(root_mount, "etc", "fstab")
    with open(fstab_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    log("fstab generated successfully.")

def attach_virtual_fs(root_mount: str, log: LogFn):
    for src, dst in [("/dev", "dev"), ("/proc", "proc"), ("/sys", "sys"), ("/run", "run")]:
        ensure_dir(os.path.join(root_mount, dst))
        run(
            f"mount --bind {shlex.quote(src)} "
            f"{shlex.quote(os.path.join(root_mount, dst))}",
            log,
        )


def detach_virtual_fs(root_mount: str, log: LogFn):
    for dst in ["run", "sys", "proc", "dev"]:
        run(
            f"umount -l {shlex.quote(os.path.join(root_mount, dst))}",
            log,
            check=False,
        )


def run_in_target(root_mount: str, cmd: str, log: LogFn):
    run(
        f"chroot {shlex.quote(root_mount)} /bin/bash -lc {shlex.quote(cmd)}",
        log,
    )


def replicate_live_system(root_mount: str, log: LogFn):
    excl_args = " ".join(
        f"--exclude={shlex.quote(x)}" for x in _LIVE_RSYNC_EXCLUDES
    )
    ensure_dir(root_mount)
    # -a  : archive (permisos, timestamps, symlinks, owner, group)
    # -A  : ACLs
    # -X  : xattrs extendidos
    # No -H (hardlinks): drastically reduces pre-scan time.
    #   Hardlinks become independent copies — acceptable in an installer.
    # --no-whole-file: use delta transfer (faster on slow disks)
    # --checksum-choice=none: skip unnecessary checksum calculation
    run(
        f"rsync -aAX --no-whole-file {excl_args} / {shlex.quote(root_mount)}/",
        log,
    )

def scrub_live_residue(root_mount: str, log: LogFn):
    for rel in _LIVE_RESIDUE_PATHS:
        full = os.path.join(root_mount, rel)
        if os.path.isfile(full):
            os.remove(full)
            log(f"  removed: /{rel}")
        elif os.path.isdir(full):
            run(f"rm -rf {shlex.quote(full)}", log, check=False)
            log(f"  removed: /{rel}/")

    profiledir = os.path.join(root_mount, "etc", "profile.d")
    if os.path.isdir(profiledir):
        for fname in os.listdir(profiledir):
            if "live" in fname.lower():
                os.remove(os.path.join(profiledir, fname))
                log(f"  removed: /etc/profile.d/{fname}")

    initd_dir    = os.path.join(root_mount, "etc", "init.d")
    rcN_dirs     = [
        os.path.join(root_mount, "etc", d)
        for d in os.listdir(os.path.join(root_mount, "etc"))
        if d.startswith("rc") and os.path.isdir(os.path.join(root_mount, "etc", d))
    ] if os.path.isdir(os.path.join(root_mount, "etc")) else []

    runlevels_dir = os.path.join(root_mount, "etc", "runlevels")

    for script_name in _LIVE_INIT_SCRIPTS:
        script_path = os.path.join(initd_dir, script_name)

        for rcdir in rcN_dirs:
            for entry in os.listdir(rcdir) if os.path.isdir(rcdir) else []:
                if script_name in entry:
                    sym = os.path.join(rcdir, entry)
                    try:
                        os.remove(sym)
                        log(f"  disabled: {sym.replace(root_mount, '')}")
                    except Exception:
                        pass

        if os.path.isdir(runlevels_dir):
            for rl in os.listdir(runlevels_dir):
                rl_path = os.path.join(runlevels_dir, rl)
                sym = os.path.join(rl_path, script_name)
                if os.path.exists(sym) or os.path.islink(sym):
                    try:
                        os.remove(sym)
                        log(f"  disabled OpenRC: /etc/runlevels/{rl}/{script_name}")
                    except Exception:
                        pass

        if os.path.exists(script_path):
            try:
                os.remove(script_path)
                log(f"  removed: /etc/init.d/{script_name}")
            except Exception as e:
                log(f"  warning: could not remove /etc/init.d/{script_name}: {e}")

    if os.path.isdir(initd_dir):
        for fname in os.listdir(initd_dir):
            if fname.startswith("live-") or fname == "live":
                fpath = os.path.join(initd_dir, fname)
                try:
                    os.remove(fpath)
                    log(f"  removed residue: /etc/init.d/{fname}")
                except Exception:
                    pass

    log("Live residues removed.")

def regenerate_machine_id(root_mount: str, log: LogFn):
    for mid_rel in ["etc/machine-id", "var/lib/dbus/machine-id"]:
        full = os.path.join(root_mount, mid_rel)
        if os.path.exists(full):
            os.remove(full)

    run_in_target(
        root_mount,
        "dbus-uuidgen --ensure=/etc/machine-id 2>/dev/null || "
        "systemd-machine-id-setup 2>/dev/null || "
        "cat /proc/sys/kernel/random/uuid | tr -d '-' > /etc/machine-id",
        log,
    )
    run_in_target(
        root_mount,
        "mkdir -p /var/lib/dbus && "
        "cp /etc/machine-id /var/lib/dbus/machine-id 2>/dev/null || true",
        log,
    )
    log("machine-id regenerated.")

def deactivate_autologin(root_mount: str, log: LogFn):
    patched = []
    for rule in _DM_AUTOLOGIN_RULES:
        cfg_full = os.path.join(root_mount, rule["cfg"])
        if not os.path.exists(cfg_full):
            continue
        try:
            with open(cfg_full, "r", encoding="utf-8", errors="ignore") as f:
                original = f.read()
            updated = re.sub(rule["pattern"], rule["replace"], original, flags=re.MULTILINE)
            if updated != original:
                with open(cfg_full, "w", encoding="utf-8") as f:
                    f.write(updated)
                patched.append(rule["cfg"])
        except Exception as e:
            log(f"  warning: could not patch {rule['cfg']}: {e}")

    # OpenRC / getty with autologin (Devuan)
    sv_dir = os.path.join(root_mount, "etc", "sv")
    if os.path.isdir(sv_dir):
        run(
            f"grep -rl 'getty.*-a' {shlex.quote(sv_dir)} 2>/dev/null "
            f"| xargs -r sed -i 's/getty\\(.*\\)-a [^ ]*/getty\\1/g'",
            log,
            check=False,
        )

    if patched:
        log(f"Autologin disabled in: {', '.join(patched)}")
    else:
        log("Autologin: no active configurations found.")

def apply_timezone(root_mount: str, tz: str, log: LogFn):
    ensure_dir(os.path.join(root_mount, "etc"))
    with open(os.path.join(root_mount, "etc", "timezone"), "w", encoding="utf-8") as f:
        f.write(tz.strip() + "\n")

    zoneinfo_src = os.path.join(root_mount, "usr", "share", "zoneinfo", tz)
    localtime_dst = os.path.join(root_mount, "etc", "localtime")
    if os.path.exists(zoneinfo_src):
        run(f"cp -f {shlex.quote(zoneinfo_src)} {shlex.quote(localtime_dst)}", log)
        log(f"Timezone applied: {tz}")
    else:
        log(f"WARNING: zoneinfo not found in target: {zoneinfo_src}")

def sanitize_hostname(h: str) -> str:
    h = h.strip().lower()
    h = re.sub(r"[^a-z0-9-]", "", h)
    h = re.sub(r"-{2,}", "-", h).strip("-")
    return h or "essora"


def sanitize_username(u: str) -> str:
    u = u.strip().lower()
    u = re.sub(r"[^a-z0-9_-]", "", u)
    if not u or u[0].isdigit():
        u = "essora"
    return u


def _sanitize_kb_value(s: str, allowed: str) -> str:
    s = (s or "").strip()
    s = re.sub(rf"[^{allowed}]", "", s)
    return s[:128]

def prepare_partition(dev: str, fstype: str, label: str, log: LogFn):
    fstype = (fstype or "").strip().lower()
    if fstype not in ("ext4", "ext3"):
        raise RuntimeError("Only ext4/ext3 filesystems are supported.")
    label = (label or "essora")[:16]
    run(f"mkfs.{fstype} -F -L {shlex.quote(label)} {shlex.quote(dev)}", log)
    log(f"Partition formatted: {fstype}, label '{label}'.")

def verify_disk_space(root_part: str, log: LogFn):
    try:
        out = subprocess.check_output(
            ["df", "-B1", "--output=avail", root_part], text=True
        )
        avail = int(out.strip().splitlines()[-1])

        out2 = subprocess.check_output(
            ["du", "-sxb", "/"], text=True, stderr=subprocess.DEVNULL
        )
        used = int(out2.split()[0])
        needed = int(used * 1.10)

        avail_g  = avail  / 1024 ** 3
        needed_g = needed / 1024 ** 3
        log(f"Required space: ~{needed_g:.1f} GB  |  Available: {avail_g:.1f} GB")

        if avail < needed:
            raise RuntimeError(
                f"Not enough space on {root_part}: "
                f"need {needed_g:.1f} GB but only {avail_g:.1f} GB available."
            )
    except RuntimeError:
        raise
    except Exception as e:
        log(f"WARNING: could not verify disk space: {e}")

def resolve_live_user(root_mount: str) -> Optional[str]:
    passwd_path = os.path.join(root_mount, "etc", "passwd")
    if not os.path.exists(passwd_path):
        return None
    try:
        with open(passwd_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 3 and parts[2] == "1000":
                    return parts[0]
    except Exception:
        pass
    return None


def provision_user(
    root_mount: str,
    username: str,
    password: str,
    hostname: str,
    log: LogFn,
):
    hostname = sanitize_hostname(hostname)
    username = sanitize_username(username)

    # hostname
    with open(os.path.join(root_mount, "etc", "hostname"), "w", encoding="utf-8") as f:
        f.write(hostname + "\n")

    hosts_path = os.path.join(root_mount, "etc", "hosts")
    if not os.path.exists(hosts_path):
        with open(hosts_path, "w", encoding="utf-8") as f:
            f.write("127.0.0.1\tlocalhost\n")
            f.write(f"127.0.1.1\t{hostname}\n")
    else:
        with open(hosts_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if hostname not in content:
            with open(hosts_path, "a", encoding="utf-8") as f:
                f.write(f"127.0.1.1\t{hostname}\n")

    live_user = resolve_live_user(root_mount)
    if live_user and live_user != username:
        log(f"Renaming live user '{live_user}' -> '{username}'")
        run_in_target(root_mount, f"usermod -l {shlex.quote(username)} {shlex.quote(live_user)}", log)
        run_in_target(root_mount, f"groupmod -n {shlex.quote(username)} {shlex.quote(live_user)} 2>/dev/null || true", log)
        run_in_target(root_mount, f"usermod -d /home/{shlex.quote(username)} -m {shlex.quote(username)}", log)
        new_home = os.path.join(root_mount, "home", username)
        for config_subdir in [".config", ".local"]:
            search_path = os.path.join(new_home, config_subdir)
            if os.path.isdir(search_path):
                run(
                    f"grep -rl {shlex.quote('/home/' + live_user)} {shlex.quote(search_path)} "
                    f"2>/dev/null | xargs -r sed -i "
                    f"s|{shlex.quote('/home/' + live_user)}|{shlex.quote('/home/' + username)}|g",
                    log, check=False,
                )
    else:
        run_in_target(
            root_mount,
            f"getent passwd {shlex.quote(username)} >/dev/null || "
            f"useradd -m -s /bin/bash {shlex.quote(username)}",
            log,
        )

    # common groups in Devuan/Essora
    essential_groups = "sudo,audio,video,plugdev,netdev,cdrom,floppy,dialout"
    run_in_target(
        root_mount,
        f"usermod -aG {essential_groups} {shlex.quote(username)} || true",
        log,
    )

    safe_line = f"{username}:{password}"
    run_in_target(root_mount, f"printf %s {shlex.quote(safe_line)} | chpasswd", log)
    log(f"User '{username}' configured successfully.")


def configure_root_access(
    root_mount: str,
    root_password: str,
    lock_root: bool,
    log: LogFn,
):
    if (root_password or "").strip():
        safe_line = f"root:{root_password}"
        run_in_target(root_mount, f"printf %s {shlex.quote(safe_line)} | chpasswd", log)
        run_in_target(root_mount, "passwd -u root || true", log)
        log("Root password set.")
        return
    if lock_root:
        run_in_target(root_mount, "passwd -l root || true", log)
        log("Root account locked.")
    else:
        log("Root: no changes.")

def apply_keyboard_settings(
    root_mount: str,
    layout: str,
    model: str,
    variant: str,
    options: str,
    log: LogFn,
):
    layout  = _sanitize_kb_value(layout,  r"A-Za-z0-9,_-") or "us"
    model   = _sanitize_kb_value(model,   r"A-Za-z0-9_-")  or "pc105"
    variant = _sanitize_kb_value(variant, r"A-Za-z0-9,_-")
    options = _sanitize_kb_value(options, r"A-Za-z0-9,_:-")

    # /etc/default/keyboard
    ensure_dir(os.path.join(root_mount, "etc", "default"))
    kbd_path = os.path.join(root_mount, "etc", "default", "keyboard")
    with open(kbd_path, "w", encoding="utf-8") as f:
        f.write("# /etc/default/keyboard - generated by essora-installer\n")
        f.write(f'XKBMODEL="{model}"\n')
        f.write(f'XKBLAYOUT="{layout}"\n')
        f.write(f'XKBVARIANT="{variant}"\n')
        f.write(f'XKBOPTIONS="{options}"\n')
        f.write('BACKSPACE="guess"\n')

    # /etc/X11/xorg.conf.d/00-keyboard.conf
    xorg_dir = os.path.join(root_mount, "etc", "X11", "xorg.conf.d")
    ensure_dir(xorg_dir)
    xorg_path = os.path.join(xorg_dir, "00-keyboard.conf")
    with open(xorg_path, "w", encoding="utf-8") as f:
        f.write('Section "InputClass"\n')
        f.write('    Identifier "system-keyboard"\n')
        f.write('    MatchIsKeyboard "on"\n')
        f.write(f'    Option "XkbLayout" "{layout}"\n')
        f.write(f'    Option "XkbModel" "{model}"\n')
        if variant:
            f.write(f'    Option "XkbVariant" "{variant}"\n')
        if options:
            f.write(f'    Option "XkbOptions" "{options}"\n')
        f.write("EndSection\n")

    log(f"Keyboard configured: layout={layout}, model={model}.")

def deploy_grub(root_mount: str, grub_disk: str, uefi: bool, log: LogFn,
                efi_part: Optional[str] = None):
    if not grub_disk.startswith("/dev/"):
        raise RuntimeError("Invalid GRUB disk.")

    if uefi:
        efi_mount = os.path.join(root_mount, "boot", "efi")


        if efi_part and efi_part.startswith("/dev/"):
            log(f"── Reformatting EFI partition {efi_part} (removes old boot entries)...")
            run(f"umount -l {shlex.quote(efi_mount)} 2>/dev/null || true", log, check=False)
            run(f"mkfs.fat -F32 -n EFI {shlex.quote(efi_part)}", log)
            run(f"mount {shlex.quote(efi_part)} {shlex.quote(efi_mount)}", log)


        run(
            "efibootmgr 2>/dev/null | grep -iE 'Essora|grub' | "
            "grep -o 'Boot[0-9A-F][0-9A-F][0-9A-F][0-9A-F]' | "
            "sed 's/Boot//' | "
            "xargs -r -I% efibootmgr -b % -B 2>/dev/null || true",
            log, check=False
        )

        run_in_target(
            root_mount,
            "grub-install --target=x86_64-efi "
            "--efi-directory=/boot/efi "
            "--bootloader-id=debian "
            "--recheck "
            "--force",
            log,
        )
    else:
        run_in_target(
            root_mount,
            f"grub-install --target=i386-pc {shlex.quote(grub_disk)} --recheck --force",
            log,
        )


    if uefi:
        import shutil as _shutil
        efi_fw_dir = os.path.join(root_mount, "boot", "efi", "EFI")
        boot_dir   = os.path.join(efi_fw_dir, "boot")
        os.makedirs(boot_dir, exist_ok=True)
        for candidate in ("debian", "Essora", "essora", "devuan", "grub"):
            src_dir = os.path.join(efi_fw_dir, candidate)
            if not os.path.isdir(src_dir):
                continue
            for grub_efi in ("grubx64.efi", "shimx64.efi", "grub.efi"):
                src_f = os.path.join(src_dir, grub_efi)
                if os.path.exists(src_f):
                    try:
                        _shutil.copy2(src_f, os.path.join(boot_dir, "bootx64.efi"))
                        log(f"  EFI fallback: {candidate}/{grub_efi} -> EFI/boot/bootx64.efi")
                    except Exception as e:
                        log(f"  WARNING: EFI fallback failed: {e}")
                    break
            else:
                continue
            break

    run_in_target(root_mount, "update-grub", log)
    log("GRUB installed and configured.")


def get_ram_bytes() -> int:
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb * 1024
    except Exception:
        pass
    return 4 * 1024 ** 3  # fallback 4 GB


def calc_swap_size_bytes(ram_bytes: int) -> int:
    four_gb = 4 * 1024 ** 3
    if ram_bytes <= four_gb:
        return four_gb         
    else:
        return ram_bytes // 2  


def partition_whole_disk(disk: str, uefi: bool, log: LogFn) -> dict:
    """Wipe disk and create: EFI (1024 MiB, FAT32) + swap + root (ext4).
    Returns dict with keys: efi_part, swap_part, root_part (strings like /dev/sda1).
    """
    ram = get_ram_bytes()
    swap_bytes = calc_swap_size_bytes(ram)
    swap_mib = swap_bytes // (1024 ** 2)
    ram_gb = ram / 1024 ** 3
    swap_gb = swap_mib / 1024
    log(f"Whole-disk mode: RAM={ram_gb:.1f} GB -> swap={swap_gb:.1f} GB")

    log(f"Wiping partition table on {disk}...")
    run(f"wipefs -a {shlex.quote(disk)}", log)
    run(f"sgdisk -Z {shlex.quote(disk)}", log, check=False)

    if uefi:
        log("Creating GPT partition table (UEFI)...")
        run(f"parted -s {shlex.quote(disk)} mklabel gpt", log)
        # Part 1: EFI 1024 MiB
        run(f"parted -s {shlex.quote(disk)} mkpart primary fat32 1MiB 1025MiB", log)
        run(f"parted -s {shlex.quote(disk)} set 1 esp on", log)
        # Part 2: swap
        swap_end_mib = 1025 + swap_mib
        run(f"parted -s {shlex.quote(disk)} mkpart primary linux-swap 1025MiB {swap_end_mib}MiB", log)
        # Part 3: root (rest)
        run(f"parted -s {shlex.quote(disk)} mkpart primary ext4 {swap_end_mib}MiB 100%", log)
    else:
        log("Creating MBR partition table (BIOS/Legacy)...")
        run(f"parted -s {shlex.quote(disk)} mklabel msdos", log)
        # Part 1: swap
        swap_end_mib = 1 + swap_mib
        run(f"parted -s {shlex.quote(disk)} mkpart primary linux-swap 1MiB {swap_end_mib}MiB", log)
        # Part 2: root (rest)
        run(f"parted -s {shlex.quote(disk)} mkpart primary ext4 {swap_end_mib}MiB 100%", log)
        run(f"parted -s {shlex.quote(disk)} set 2 boot on", log)

    run("partprobe || udevadm settle || sleep 2", log, check=False)

    # Resolve partition paths
    def part_path(disk: str, num: int) -> str:
        if re.match(r"^/dev/(nvme|mmcblk)", disk):
            return f"{disk}p{num}"
        return f"{disk}{num}"

    if uefi:
        efi_part  = part_path(disk, 1)
        swap_part = part_path(disk, 2)
        root_part = part_path(disk, 3)
        log(f"Formatting EFI partition {efi_part} as FAT32...")
        run(f"mkfs.fat -F32 {shlex.quote(efi_part)}", log)
    else:
        efi_part  = None
        swap_part = part_path(disk, 1)
        root_part = part_path(disk, 2)

    log(f"Initializing swap on {swap_part}...")
    run(f"mkswap -L essora-swap {shlex.quote(swap_part)}", log)

    log(f"Partitioning complete: root={root_part}, swap={swap_part}, efi={efi_part or 'none'}")
    return {"efi_part": efi_part, "swap_part": swap_part, "root_part": root_part}

def do_install(plan: InstallPlan, log: LogFn, progress: Callable[[int], None]):
    if not is_root():
        raise RuntimeError("The installer must be run as root (pkexec).")

    root_mount = "/mnt/target"
    home_mount = "/mnt/target-home" if plan.home_part else None

    plan.hostname    = sanitize_hostname(plan.hostname)
    plan.username    = sanitize_username(plan.username)
    plan.root_fstype = (plan.root_fstype or "ext4").lower().strip()
    plan.kb_layout   = plan.kb_layout or "us"
    plan.kb_model    = plan.kb_model  or "pc105"

    progress(1)
    log("── Verifying disk space...")
    verify_disk_space(plan.root_part, log)

    progress(3)
    log("── Cleaning previous mounts...")
    detach_mounts(root_mount, log)
    if home_mount:
        detach_mounts(home_mount, log)
    ensure_dir(root_mount)

    progress(5)
    if plan.format_root:
        log("── Formatting root partition...")
        prepare_partition(plan.root_part, plan.root_fstype, detect_de_label(), log)

    if plan.home_part and plan.format_home:
        log("── Formatting /home partition...")
        prepare_partition(plan.home_part, plan.home_fstype, "essora-home", log)

    progress(8)
    log("── Mounting partitions...")
    run(f"mount {shlex.quote(plan.root_part)} {shlex.quote(root_mount)}", log)
    ensure_dir(os.path.join(root_mount, "boot", "efi"))

    if plan.efi_part:
        # Format EFI BEFORE mounting — gives fresh UUID for fstab
        log(f"── Formatting EFI partition {plan.efi_part} as FAT32...")
        run(f"mkfs.fat -F32 -n EFI {shlex.quote(plan.efi_part)}", log)
        run("udevadm settle 2>/dev/null || true", log, check=False)
        run("sync", log, check=False)
        run(
            f"mount {shlex.quote(plan.efi_part)} "
            f"{shlex.quote(os.path.join(root_mount, 'boot/efi'))}",
            log,
        )

    if plan.home_part:
        ensure_dir(home_mount)
        run(f"mount {shlex.quote(plan.home_part)} {shlex.quote(home_mount)}", log)
        ensure_dir(os.path.join(root_mount, "home"))
        run(
            f"mount --bind {shlex.quote(home_mount)} "
            f"{shlex.quote(os.path.join(root_mount, 'home'))}",
            log,
        )

    if plan.swap_part and plan.format_swap:
        log(f"── Initializing swap on {plan.swap_part}...")
        run(f"mkswap -L essora-swap {shlex.quote(plan.swap_part)}", log)
    if plan.swap_part:
        run(f"swapon {shlex.quote(plan.swap_part)}", log, check=False)

    progress(10)
    log("── Copying live system to disk (rsync)...")
    replicate_live_system(root_mount, log)

    progress(65)
    log("── Removing live environment residues...")
    scrub_live_residue(root_mount, log)

    progress(67)
    log("── Generating /etc/fstab...")
    generate_fstab(root_mount, plan.root_part, plan.efi_part, plan.home_part, log, plan.swap_part)

    progress(69)
    log("── Configuring timezone...")
    apply_timezone(root_mount, plan.timezone, log)

    progress(71)
    log("── Configuring keyboard...")
    apply_keyboard_settings(
        root_mount,
        plan.kb_layout, plan.kb_model,
        plan.kb_variant, plan.kb_options,
        log,
    )

    progress(73)
    log("── Preparing chroot environment...")
    attach_virtual_fs(root_mount, log)

    try:
        run_in_target(
            root_mount,
            "command -v setupcon >/dev/null 2>&1 && "
            "setupcon --keyboard-only --force || true",
            log,
        )

        progress(75)
        log("── Regenerating machine-id...")
        regenerate_machine_id(root_mount, log)

        progress(77)
        log("── Disabling live autologin...")
        deactivate_autologin(root_mount, log)

        progress(80)
        log("── Configuring main user account...")
        provision_user(root_mount, plan.username, plan.password, plan.hostname, log)

        progress(84)
        log("── Configuring root access...")
        configure_root_access(root_mount, plan.root_password, plan.lock_root, log)

        if plan.install_grub:
            progress(87)
            log("── Installing GRUB...")
            if plan.uefi and not plan.efi_part:
                log("WARNING: UEFI detected but no EFI partition selected. GRUB may fail.")
            deploy_grub(root_mount, plan.grub_disk, plan.uefi, log, plan.efi_part)

        progress(92)
        log("── Running post-install cleanup on the installed system...")
        _post_install_in_target(root_mount, plan.username, plan.slim_autologin, log)

    finally:
        progress(95)
        log("── Unmounting virtual filesystems...")
        detach_virtual_fs(root_mount, log)

    log("── Unmounting partitions...")
    if plan.efi_part:
        run(
            f"umount -l {shlex.quote(os.path.join(root_mount, 'boot/efi'))}",
            log, check=False,
        )
    if plan.home_part:
        run(
            f"umount -l {shlex.quote(os.path.join(root_mount, 'home'))}",
            log, check=False,
        )
        run(f"umount -l {shlex.quote(home_mount)}", log, check=False)
    run(f"umount -l {shlex.quote(root_mount)}", log, check=False)

    progress(100)
    log("Installation complete. You may reboot into the new system.")

_LIVE_USER_NAME = "essora"


UNINSTALL_LIST = "/usr/local/essora-installer/uninstall"


def _remove_installer_package_from_target(root_mount: str, log: LogFn) -> None:
    """Purge packages listed in /usr/local/essora-installer/uninstall."""
    list_path = os.path.join(root_mount, UNINSTALL_LIST.lstrip("/"))
    if not os.path.isfile(list_path):
        log(f"  [post] {UNINSTALL_LIST} not found, skipping package removal.")
        return
    try:
        with open(list_path, "r", encoding="utf-8", errors="ignore") as f:
            packages = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except Exception as e:
        log(f"  [post] Could not read uninstall list: {e}")
        return
    if not packages:
        return
    pkg_list = " ".join(shlex.quote(p) for p in packages)
    log(f"  [post] Purging packages: {', '.join(packages)}")
    run_in_target(
        root_mount,
        f"apt-get purge -y {pkg_list} 2>/dev/null || true",
        log,
    )


def _post_install_in_target(
    root_mount: str,
    chosen_username: str,
    slim_autologin: bool,
    log: LogFn,
) -> None:

    if chosen_username.lower() == _LIVE_USER_NAME:
        log(f"  [post] Chosen user is '{chosen_username}': not removed, already configured.")
    else:
        _remove_live_user_from_target(root_mount, log)

    _remove_installer_desktop_from_target(root_mount, log)
    _remove_installer_package_from_target(root_mount, log)

    _configure_slim_in_target(root_mount, chosen_username, slim_autologin, log)

    _enable_networkmanager_in_target(root_mount, log)

    _configure_plasma_locale(root_mount, chosen_username, log)


def _remove_live_user_from_target(root_mount: str, log: LogFn) -> None:
    live = _LIVE_USER_NAME
    log(f"  [post] Removing live user '{live}' from the installed system...")

    system_files = [
        "etc/passwd",
        "etc/shadow",
        "etc/group",
        "etc/gshadow",
        "etc/subuid",
        "etc/subgid",
    ]
    for rel in system_files:
        fpath = os.path.join(root_mount, rel)
        if not os.path.isfile(fpath):
            log(f"    (/{rel} does not exist, skipping)")
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            new_lines = [l for l in lines if not l.startswith(f"{live}:")]
            if len(new_lines) != len(lines):
                with open(fpath, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                log(f"    cleaned: /{rel}")
        except Exception as e:
            log(f"    WARNING: could not clean /{rel}: {e}")

    home_in_target = os.path.join(root_mount, "home", live)
    if os.path.isdir(home_in_target):
        run(f"rm -rf {shlex.quote(home_in_target)}", log, check=False)
        log(f"    removed: /home/{live}")

    for mail_rel in [f"var/mail/{live}", f"var/spool/mail/{live}"]:
        mail_path = os.path.join(root_mount, mail_rel)
        if os.path.isfile(mail_path):
            os.remove(mail_path)
            log(f"    removed: /{mail_rel}")

    log(f"  [post] User '{live}' removed from the installed system.")


def _remove_installer_desktop_from_target(root_mount: str, log: LogFn) -> None:
    log("  [post] Removing installer shortcuts from the installed system...")

    target_user = resolve_live_user(root_mount)  

    desktop_candidates = [
        os.path.join(root_mount, "usr", "share", "applications", "essora-installer.desktop"),
    ]
    if target_user:
        desktop_candidates.append(
            os.path.join(root_mount, "home", target_user, "Desktop", "essora-installer.desktop")
        )
    desktop_candidates.append(
        os.path.join(root_mount, "home", _LIVE_USER_NAME, "Desktop", "essora-installer.desktop")
    )

    for path in desktop_candidates:
        if os.path.isfile(path):
            try:
                os.remove(path)
                log(f"    removed: {path.replace(root_mount, '')}")
            except Exception as e:
                log(f"    WARNING: could not remove {path}: {e}")


def _configure_slim_in_target(
    root_mount: str,
    username: str,
    autologin: bool,
    log: LogFn,
) -> None:
    slim_conf = os.path.join(root_mount, "etc", "slim.conf")
    if not os.path.isfile(slim_conf):
        log("  [post] /etc/slim.conf not found in target, skipping.")
        return

    log(f"  [post] Configuring SLiM: default_user={username}, auto_login={'yes' if autologin else 'no'}")

    try:
        with open(slim_conf, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        new_lines: List[str] = []
        seen_default_user = False
        seen_auto_login = False

        for line in lines:
            stripped = line.rstrip()

            # default_user 
            if re.match(r"^\s*#?\s*default_user\b", stripped):
                if not seen_default_user:
                    new_lines.append(f"default_user        {username}\n")
                    seen_default_user = True
                
                continue

            # auto_login 
            if re.match(r"^\s*#?\s*auto_login\b", stripped):
                if not seen_auto_login:
                    val = "yes" if autologin else "no"
                    new_lines.append(f"auto_login          {val}\n")
                    seen_auto_login = True
                continue

            new_lines.append(line)

        if not seen_default_user:
            new_lines.append(f"default_user        {username}\n")
            log("    default_user appended to slim.conf")
        if not seen_auto_login:
            val = "yes" if autologin else "no"
            new_lines.append(f"auto_login          {val}\n")
            log("    auto_login appended to slim.conf")

        with open(slim_conf, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        log("  [post] slim.conf updated successfully.")

    except Exception as e:
        log(f"  [post] WARNING: error configuring slim.conf: {e}")


def _enable_networkmanager_in_target(root_mount: str, log: LogFn) -> None:
    runlevel_dir = os.path.join(root_mount, "etc", "runlevels", "default")
    nm_init      = os.path.join(root_mount, "etc", "init.d", "network-manager")
    nm_link      = os.path.join(runlevel_dir, "network-manager")

    if not os.path.isfile(nm_init):
        log("  [post] network-manager init script not found in target, skipping.")
        return

    if os.path.exists(nm_link):
        log("  [post] network-manager already enabled in OpenRC (symlink exists).")
        return

    try:
        os.makedirs(runlevel_dir, exist_ok=True)
        os.symlink(nm_init.replace(root_mount, ""), nm_link)
        log("  [post] network-manager enabled in OpenRC (default runlevel).")
    except Exception as e:
        log(f"  [post] WARNING: could not enable network-manager: {e}")

def list_partitions() -> List[Dict[str, Any]]:
    try:
        out = subprocess.check_output(
            ["lsblk", "-J", "-o", "PATH,SIZE,FSTYPE,LABEL,MOUNTPOINT,TYPE,PARTTYPENAME"],
            text=True,
        )
        data = json.loads(out)
    except Exception:
        return []

    result: List[Dict[str, Any]] = []

    def _walk(devices):
        for dev in devices:
            if dev.get("type") in ("part", "lvm"):
                result.append({
                    "path":         dev.get("path") or "",
                    "size":         dev.get("size") or "",
                    "fstype":       dev.get("fstype") or "",
                    "label":        dev.get("label") or "",
                    "mountpoint":   dev.get("mountpoint") or "",
                    "parttypename": dev.get("parttypename") or "",
                })
            if dev.get("children"):
                _walk(dev["children"])

    _walk(data.get("blockdevices", []) or [])
    return result


def list_disks() -> List[Dict[str, Any]]:
    try:
        out = subprocess.check_output(
            ["lsblk", "-J", "-o", "PATH,SIZE,MODEL,TYPE"],
            text=True,
        )
        data = json.loads(out)
    except Exception:
        return []

    return [
        {
            "path":  dev.get("path") or "",
            "size":  dev.get("size") or "",
            "model": (dev.get("model") or "").strip(),
        }
        for dev in (data.get("blockdevices", []) or [])
        if dev.get("type") == "disk"
    ]


def _configure_plasma_locale(
    root_mount: str,
    username: str,
    log: LogFn,
) -> None:

    kde_detected = False

    home_base = "/home"
    if os.path.isdir(home_base):
        for user_dir in os.listdir(home_base):
            xsession = os.path.join(home_base, user_dir, ".xsession")
            if os.path.isfile(xsession):
                try:
                    with open(xsession, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if "startkde" in content:
                        kde_detected = True
                        log(f"  [plasma] KDE detected in /home/{user_dir}/.xsession")
                        break
                except Exception:
                    pass

    if not kde_detected:
        skel_xsession = "/etc/skel/.xsession"
        if os.path.isfile(skel_xsession):
            try:
                with open(skel_xsession, "r", encoding="utf-8", errors="ignore") as f:
                    if "startkde" in f.read():
                        kde_detected = True
                        log("  [plasma] KDE detected in /etc/skel/.xsession")
            except Exception:
                pass

    if not kde_detected:
        log("  [plasma] KDE/Plasma not detected, skipping plasma-localerc.")
        return

    locale_conf = os.path.join(root_mount, "etc", "locale.conf")
    locale_vars: dict = {}

    if os.path.isfile(locale_conf):
        try:
            with open(locale_conf, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        key, _, val = line.partition("=")
                        locale_vars[key.strip()] = val.strip().strip('"\'')
        except Exception as e:
            log(f"  [plasma] WARNING: could not read /etc/locale.conf: {e}")
    else:
        log("  [plasma] /etc/locale.conf not found in target, using en_US.UTF-8.")

    lang     = locale_vars.get("LANG", "en_US.UTF-8")
    monetary = locale_vars.get("LC_MONETARY", lang)
    paper    = locale_vars.get("LC_PAPER", lang)

    lang_code = lang.split(".")[0] if "." in lang else lang

    plasma_content = (
        "[Formats]\n"
        f"LANG={lang}\n"
        f"LC_MONETARY={monetary}\n"
        f"LC_PAPER={paper}\n"
        "\n"
        "[Translations]\n"
        f"LANGUAGE={lang_code}\n"
    )

    skel_config = os.path.join(root_mount, "etc", "skel", ".config")
    os.makedirs(skel_config, exist_ok=True)
    skel_dest = os.path.join(skel_config, "plasma-localerc")
    try:
        with open(skel_dest, "w", encoding="utf-8") as f:
            f.write(plasma_content)
        log("  [plasma] Written: /etc/skel/.config/plasma-localerc")
    except Exception as e:
        log(f"  [plasma] WARNING: could not write to skel: {e}")

    user_config = os.path.join(root_mount, "home", username, ".config")
    os.makedirs(user_config, exist_ok=True)
    user_dest = os.path.join(user_config, "plasma-localerc")
    try:
        with open(user_dest, "w", encoding="utf-8") as f:
            f.write(plasma_content)
        passwd_path = os.path.join(root_mount, "etc", "passwd")
        uid, gid = None, None
        if os.path.isfile(passwd_path):
            with open(passwd_path, "r", encoding="utf-8", errors="ignore") as pf:
                for line in pf:
                    parts = line.strip().split(":")
                    if len(parts) >= 4 and parts[0] == username:
                        try:
                            uid = int(parts[2])
                            gid = int(parts[3])
                        except ValueError:
                            pass
                        break
        if uid is not None:
            os.chown(user_dest, uid, gid)
            os.chown(user_config, uid, gid)
        log(f"  [plasma] Written: /home/{username}/.config/plasma-localerc")
    except Exception as e:
        log(f"  [plasma] WARNING: could not write for user {username}: {e}")

    log(f"  [plasma] plasma-localerc configured: LANG={lang}, LANGUAGE={lang_code}")


def is_uefi_firmware() -> bool:
    return os.path.isdir("/sys/firmware/efi")


def parent_disk(device_path: str) -> str:
    if re.match(r"^/dev/(nvme\d+n\d+|mmcblk\d+)p\d+$", device_path):
        return re.sub(r"p\d+$", "", device_path)
    return re.sub(r"\d+$", "", device_path)
