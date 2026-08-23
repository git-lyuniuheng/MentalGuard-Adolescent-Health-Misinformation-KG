# -*- coding: utf-8 -*-
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_mh import MH_SRC, MH_NEW
from data_fs import FS_SRC, FS_NEW
from data_vx import VX_SRC, VX_NEW
from data_dh import DH_SRC, DH_NEW
from data_ss import SS_SRC, SS_NEW
from data_bn import BN_SRC, BN_NEW
from data_dm import DM_SRC, DM_NEW
from data_sh import SH_SRC, SH_NEW
from data_sx import SX_SRC, SX_NEW

mods = [
    ("MH", MH_SRC, MH_NEW), ("FS", FS_SRC, FS_NEW), ("VX", VX_SRC, VX_NEW),
    ("DH", DH_SRC, DH_NEW), ("SS", SS_SRC, SS_NEW), ("BN", BN_SRC, BN_NEW),
    ("DM", DM_SRC, DM_NEW), ("SH", SH_SRC, SH_NEW), ("SX", SX_SRC, SX_NEW),
]
for name, SRC, NEW in mods:
    max_valid = len(SRC) - 1
    bad = []
    for i, item in enumerate(NEW):
        for ix in item[2]:
            if ix < 0 or ix > max_valid:
                bad.append((i, item[0][:20], ix))
    print(f"{name}: SRC={len(SRC)} (valid 0-{max_valid}), NEW={len(NEW)}, BAD={len(bad)}")
    for b in bad[:10]:
        print(f"    rec#{b[0]} '{b[1]}...' idx={b[2]}")
