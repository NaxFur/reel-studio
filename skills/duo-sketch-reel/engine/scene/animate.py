"""Data-driven acting, lighting and cameras for a Nerd + Claude sketch (storyboard.json -> keyframes).

Every control is an eased key track in seconds, layered with procedural motion (lip sync from the real
voice takes, blinks, breathing, typing, bounces), then written as one keyframe per frame. Each shot has its
own camera bound to a timeline marker, so cuts are frame-exact.

Vocabulary (see references/storyboard.md): nerd keys {face, look, pose, hands, gaze, do}, claude actions
{turn, point, hop, walk, bounce, arms_up, self, lean, eyes, twitch, shake, nod}, light presets, shot presets.
"""
import math, json, os, random
import bpy
from mathutils import Vector, Quaternion, Matrix, Euler
from util import fcurves_of
from tl import Anchors, FPS, fr, tm

EASE = {
    "linear": lambda x: x,
    "ease": lambda x: x * x * (3 - 2 * x),
    "smooth": lambda x: x * x * x * (x * (x * 6 - 15) + 10),
    "out": lambda x: 1 - (1 - x) ** 3,
    "in": lambda x: x ** 3,
    "snap": lambda x: 1 - (1 - x) ** 5,
    "back": lambda x: 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2,
    "step": lambda x: 1.0 if x >= 1 else 0.0,
}


def lerp(a, b, w):
    if isinstance(a, (int, float)):
        return a + (b - a) * w
    if isinstance(a, Quaternion):
        return a.slerp(b, min(1.0, max(0.0, w)))
    if isinstance(a, Vector):
        return a.lerp(b, w)
    return tuple(x + (y - x) * w for x, y in zip(a, b))


class Track:
    def __init__(self, v0):
        self.k = [(-10.0, v0, "linear")]

    def key(self, t, v, e="ease"):
        self.k = [k for k in self.k if abs(k[0] - t) > 1e-6] + [(t, v, e)]
        self.k.sort(key=lambda k: k[0])
        return self

    def go(self, t, v, dur=0.3, e="ease"):
        """Hold the current value at t, arrive at v at t + dur (keys must be added in time order)."""
        self.k = [k for k in self.k if k[0] < t - 1e-6]
        self.key(t, self.at(t), "linear")
        return self.key(t + max(dur, 1.0 / FPS), v, e)

    def seg(self, t):
        k = self.k
        if t <= k[0][0]:
            return k[0][1], k[0][1], 0.0
        for i in range(len(k) - 1):
            t0, v0, _ = k[i]
            t1, v1, e = k[i + 1]
            if t0 <= t < t1:
                return v0, v1, EASE[e]((t - t0) / (t1 - t0))
        return k[-1][1], k[-1][1], 0.0

    def at(self, t):
        a, b, w = self.seg(t)
        return lerp(a, b, w) if not isinstance(a, str) else (a if w < 0.5 else b)


LINEAR = 1


def write(idb, path, index, vals, f0=1, interp=LINEAR):
    idb.keyframe_insert(data_path=path, index=index, frame=f0)
    fc = next(fc for fc in fcurves_of(idb.animation_data.action) if fc.data_path == path and fc.array_index == max(index, 0))
    kp = fc.keyframe_points
    while len(kp) > 0:
        kp.remove(kp[0], fast=True)
    kp.add(len(vals))
    co = []
    for i, v in enumerate(vals):
        co += [f0 + i, float(v)]
    kp.foreach_set("co", co)
    kp.foreach_set("interpolation", [interp] * len(vals))
    fc.update()


def write_vec(idb, path, frames_vals, size, f0=1):
    for i in range(size):
        write(idb, path, i, [v[i] for v in frames_vals], f0)


def quat_frame(fingers, palm):
    f = Vector(fingers).normalized()
    p = Vector(palm)
    p = (p - f * p.dot(f)).normalized()
    return Matrix((f, p, f.cross(p))).transposed().to_quaternion()


def face_angle(src, dst, prev=None):
    """Mascot yaw so its front (-Y) points from src to dst (unwrapped next to prev)."""
    d = Vector(tuple(dst)[:2]) - Vector(tuple(src)[:2])
    a = math.atan2(d.x, -d.y)
    if prev is not None:
        while a - prev > math.pi: a -= 2 * math.pi
        while a - prev < -math.pi: a += 2 * math.pi
    return a


# ------------------------------------------------------------------ set geometry (matches env.py)
SPOTS = {"desk": Vector((0.33, 0.16, 0.75)), "edge": Vector((0.47, 0.0, 0.75)), "kb": Vector((0.25, 0.02, 0.75))}
CAM_LESSON = Vector((0.98, -0.30, 0.92))
HEAD0 = Vector((0.0, -0.25, 1.20))
POINTS = {
    "nerd": Vector((0.0, -0.30, 1.15)), "center": Vector((0.0, 0.47, 1.105)), "screen": Vector((0.0, 0.47, 1.105)),
    "left": Vector((-0.585, 0.335, 1.07)), "right": Vector((0.585, 0.335, 1.07)), "lens": CAM_LESSON,
    "cheat": Vector((0.22, -0.50, 0.9)), "keyboard": Vector((-0.02, 0.10, 0.76)), "nerd_lens": Vector((-0.10, 0.27, 1.00)),
    "up": Vector((0.0, 0.47, 1.40)), "down": Vector((0.0, -0.05, 0.70)),
}
FACE_KEYS = ("raise", "inner", "open", "size", "smile", "frown", "wide", "O", "lbrow")
FACES = {
    "neutral": (0, 0, 1, 1, 0, 0, 0, 0, 0),
    "attentive": (0.003, 0.05, 1.08, 1, 0, 0, 0, 0, 0),
    "surprised": (0.008, 0.12, 1.28, 1.12, 0, 0, 0, 0.35, 0),
    "panic": (0.011, 0.20, 1.34, 1.14, 0, 0.30, 0.15, 0.55, 0),
    "exhausted": (0.0, 0.45, 0.62, 0.95, 0.0, 0.55, 0.0, 0.05, 0),
    "sad": (0.002, 0.55, 0.80, 0.98, 0.0, 0.70, 0.0, 0.0, 0),
    "confused": (0.004, 0.10, 1.10, 1.0, 0.0, 0.15, 0.0, 0.12, 0.009),
    "amazed": (0.009, 0.05, 1.25, 1.10, 0.35, 0, 0.25, 0.30, 0),
    "relief": (0.005, 0.10, 0.85, 1.0, 0.70, 0, 0.30, 0.0, 0),
    "suspicious": (0.0, 0.25, 0.58, 0.95, 0.0, 0.20, 0.0, 0.0, 0.007),
    "angry": (-0.004, -0.35, 0.80, 1.0, 0.0, 0.60, 0.20, 0.0, 0),
    "ecstatic": (0.010, 0.0, 1.22, 1.10, 1.0, 0, 0.7, 0.2, 0),
    "smug": (0.004, 0.0, 0.40, 1, 1.0, 0, 0.25, 0, 0.004),
}
POSTURES = {
    "upright": Vector((0.02, 0, 0)), "slump": Vector((0.10, 0, -0.05)), "lean_in": Vector((-0.11, 0, 0.0)),
    "lean_back": Vector((0.07, 0, 0.0)), "tilt": Vector((-0.04, 0, 0.04)), "amazed": Vector((-0.10, 0, 0.02)),
    "recoil": Vector((0.12, 0, 0.0)), "hunch": Vector((-0.06, 0, -0.03)),
}
EYES = {"flat": 0.62, "open": 1.0, "wide": 1.15, "squint": 0.40, "closed": 0.06}
ARM_POINT = Vector((0.0, -0.065, 0.045))


def look_vec(p, head=HEAD0):
    """Head look (pitch, yaw, roll) toward a world point; fitted to the hand-tuned values of eps. 1-7."""
    d = Vector(p) - head
    yaw = math.atan2(d.x, d.y)
    elev = math.atan2(d.z, math.hypot(d.x, d.y))
    return Vector((0.51 * elev + 0.107, 0.72 * yaw, 0.0))


def gather(SB, A, key):
    out = []
    for b in SB["beats"]:
        for it in b.get(key, []) or []:
            out.append((A(it.get("at"), b["id"]), b["id"], it))
    out.sort(key=lambda x: x[0])
    return out


# ------------------------------------------------------------------ main
def run(scene, TL, SB, F, N, ctr, M, L, lip):
    A = Anchors(TL)
    N_FR = TL["frames"]
    DUR = TL["duration"]
    times = [tm(f) for f in range(1, N_FR + 1)]
    arm = N["arm"]

    # ============================================================ CLAUDE (first: the Nerd looks at it)
    start_spot = SB["meta"].get("claude_spot", "desk")
    m_pos = Track(Vector(SPOTS[start_spot]))
    a0 = face_angle(SPOTS[start_spot], POINTS["nerd"])
    m_rot = Track(a0)
    m_squash = Track(Vector((1, 1, 1)))
    m_lean = Track(Vector((0, 0, 0)))
    m_eye = Track(EYES[SB["meta"].get("claude_eyes", "flat")])
    arm_o = [Track(Vector((0, 0, 0))), Track(Vector((0, 0, 0)))]
    stepping, shakes, twitches, nods = [], [], [], []

    def target_pt(name, t):
        if isinstance(name, (list, tuple)):
            return Vector(name)
        return POINTS[name]

    def turn(t, tgt, dur=0.3, e="ease"):
        ang = face_angle(m_pos.at(t + dur), target_pt(tgt, t), m_rot.at(t))
        m_rot.go(t, ang, dur, e)

    def bounce(t, amt=1.0):
        m_squash.go(t - 0.03, Vector((1, 1, 1)), 0.01, "linear")
        m_squash.key(t + 0.08, Vector((1 + 0.05 * amt, 1 + 0.05 * amt, 1 - 0.09 * amt)), "out")
        m_squash.key(t + 0.30, Vector((1, 1, 1)), "ease")

    def hop(t, to=None, h=0.07, dur=0.30):
        frm = m_pos.at(t)
        to = Vector(SPOTS[to]) if to else frm.copy()
        m_squash.go(t - 0.10, Vector((1, 1, 1)), 0.01, "linear")
        m_squash.key(t, Vector((1.08, 1.08, 0.84)), "out")
        m_squash.key(t + 0.08, Vector((0.94, 0.94, 1.12)), "out")
        m_squash.key(t + dur, Vector((1.06, 1.06, 0.88)), "in")
        m_squash.key(t + dur + 0.18, Vector((1, 1, 1)), "ease")
        m_pos.go(t + 0.02, frm.lerp(to, 0.5) + Vector((0, 0, h)), dur / 2, "out")
        m_pos.key(t + dur, to, "in")

    acts = gather(SB, A, "claude")
    for i, (t, bid, it) in enumerate(acts):
        do = it.get("do")
        nxt = acts[i + 1][0] if i + 1 < len(acts) else DUR
        until = A(it["until"], bid) if "until" in it else min(nxt - 0.02, t + it.get("hold", 1.4))
        if do == "turn":
            turn(t, it.get("to", "nerd"), it.get("dur", 0.3), it.get("ease", "ease"))
        elif do == "point":
            turn(t - 0.12, it.get("to", "center"), 0.24, "snap")
            k = 0 if it.get("arm", "L") == "L" else 1
            arm_o[k].go(t - 0.05, ARM_POINT, 0.17, "back")
            arm_o[k].go(until - 0.12, Vector((0, 0, 0)), 0.12, "ease")
            bounce(t + 0.02, 1.0)
        elif do == "hop":
            hop(t, it.get("to"), it.get("h", 0.07), it.get("dur", 0.30))
            if it.get("face"):
                turn(t, it["face"], 0.30)
        elif do == "walk":
            to = Vector(SPOTS[it["to"]])
            d = it.get("dur", 0.6)
            turn(t - 0.05, (to.x, to.y, 0.75), 0.2)
            m_pos.go(t + 0.05, to, d, "ease")
            stepping.append((t + 0.05, t + 0.05 + d))
            if it.get("face"):
                turn(t + d - 0.05, it["face"], 0.3, "smooth")
        elif do == "bounce":
            bounce(t, it.get("amt", 1.0))
        elif do == "arms_up":
            for k in (0, 1):
                arm_o[k].go(t, Vector((0, 0, 0.05)), 0.2, "back")
                arm_o[k].go(until - 0.15, Vector((0, 0, 0)), 0.15)
        elif do == "self":
            for k, sgn in ((0, 1), (1, -1)):
                arm_o[k].go(t, Vector((-sgn * 0.02, -0.05, 0.02)), 0.25, "back")
                arm_o[k].go(until - 0.15, Vector((0, 0, 0)), 0.15)
        elif do == "lean":
            m_lean.go(t, Vector((0, it.get("amt", 0.12), 0)), 0.3)
            m_lean.go(until - 0.2, Vector((0, 0, 0)), 0.3)
        elif do == "eyes":
            m_eye.go(t, EYES[it.get("to", "open")], it.get("dur", 0.12), "snap")
        elif do == "twitch":
            twitches.append((t, it.get("dur", 0.75)))
            m_eye.go(t - 0.05, EYES["wide"], 0.1, "snap")
        elif do == "shake":
            shakes.append((t, it.get("dur", 0.6), it.get("amt", 0.22)))
        elif do == "nod":
            nods.append((t, it.get("dur", 0.5)))

    def m_extra_rot(t):
        r = 0.0
        for t0, d, a in shakes:
            if t0 <= t < t0 + d:
                x = (t - t0) / d
                r += a * math.sin(x * 2 * math.pi * 2) * (1 - x)
        return r

    def m_extra_lean(t):
        r = 0.0
        for t0, d in nods:
            if t0 <= t < t0 + d:
                x = (t - t0) / d
                r += 0.16 * max(0, math.sin(x * 2 * math.pi * 2)) * (1 - x)
        return r

    def twitch(t):
        for t0, d in twitches:
            if t0 <= t < t0 + d:
                return 0.20 * math.sin((t - t0) * 2 * math.pi * 11) * (1 - (t - t0) / d)
        return 0.0

    mo = lip["mascot"]["open"]
    root, body = M["root"], M["body"]
    R_loc, R_rot, B_scl, B_rot = [], [], [], []
    Ey = [[], []]; Ao = [[], []]
    arm_rest = [a.location.copy() for a in M["arms"]]
    Lz = [[] for _ in range(4)]
    leg_rest = [l.location.copy() for l in M["legs"]]
    rnd = random.Random(7)
    blinks_m, tb = [], 1.2
    while tb < DUR:
        blinks_m.append(tb); tb += rnd.uniform(3.0, 5.5)
    for f, t in zip(range(1, N_FR + 1), times):
        o = mo[f - 1] if f - 1 < len(mo) else 0.0
        step_on = 0.0
        for t0, t1 in stepping:
            if t0 <= t <= t1:
                step_on = min(1, (t - t0) / 0.1, (t1 - t) / 0.1)
        R_loc.append(tuple(m_pos.at(t) + Vector((0, 0, 0.006 * abs(math.sin(t * math.pi * 7)) * step_on))))
        R_rot.append((0, 0, m_rot.at(t) + m_extra_rot(t)))
        sq = m_squash.at(t)
        B_scl.append((sq.x, sq.y, sq.z * (1 + 0.006 * math.sin(t * 2 * math.pi / 2.6) + 0.07 * o)))
        ln_ = m_lean.at(t)
        B_rot.append((ln_.x + 0.03 * o, ln_.y + m_extra_lean(t), 0.0))
        bl = 1.0
        for b in blinks_m:
            x = (t - b) * FPS
            if -1 <= x <= 3:
                bl = min(bl, [0.5, 0.1, 0.15, 0.6, 1.0][int(x) + 1])
        ev_ = m_eye.at(t) * bl
        Ey[0].append((1, 1, ev_ + twitch(t))); Ey[1].append((1, 1, ev_))
        for k in (0, 1):
            Ao[k].append(tuple(arm_rest[k] + arm_o[k].at(t)))
        for i in range(4):
            Lz[i].append(tuple(leg_rest[i] + Vector((0, 0, step_on * max(0, math.sin(t * math.pi * 7 + i * 1.57)) * 0.012))))
    write_vec(root, "location", R_loc, 3)
    write_vec(root, "rotation_euler", R_rot, 3)
    write_vec(body, "scale", B_scl, 3)
    write_vec(body, "rotation_euler", B_rot, 3)
    for i, e in enumerate(M["eyes"]):
        write_vec(e, "scale", Ey[i], 3)
    for i, a in enumerate(M["arms"]):
        write_vec(a, "location", Ao[i], 3)
    for i, lg in enumerate(M["legs"]):
        write_vec(lg, "location", Lz[i], 3)

    mascot_eye = lambda t: m_pos.at(t) + Vector((0, 0, 0.10))

    # ============================================================ NERD
    meta_n = SB["meta"].get("nerd_start", {})
    spine = Track(Vector(POSTURES[meta_n.get("pose", "upright")]))
    look = Track(Vector((0, 0, 0)))
    gaze = Track(Vector((0, 0)))
    face = Track(FACES[meta_n.get("face", "neutral")])
    hands_start = meta_n.get("hands", ["desk", "mouse"])
    handL, handR = Track(hands_start[0]), Track(hands_start[1])
    offL, offR = Track(Vector((0, 0, 0))), Track(Vector((0, 0, 0)))
    head_shakes = []

    def look_target(name, t):
        if name == "mascot":
            return look_vec(mascot_eye(t))
        if isinstance(name, (list, tuple)):
            return look_vec(Vector(name))
        return look_vec(POINTS[name])

    look.key(-10, look_target(meta_n.get("look", "screen"), 0.0), "linear")
    extra_blinks = []
    nkeys = gather(SB, A, "nerd")
    for i, (t, bid, it) in enumerate(nkeys):
        nxt = nkeys[i + 1][0] if i + 1 < len(nkeys) else DUR
        until = A(it["until"], bid) if "until" in it else min(nxt - 0.05, t + 1.2)
        if "face" in it:
            face.go(t, FACES[it["face"]], it.get("fdur", 0.15), "snap")
            extra_blinks.append(t + 0.02)
        if "look" in it:
            v = look_target(it["look"], t) + Vector(it.get("look_off", (0, 0, 0)))
            look.go(t, v, it.get("ldur", 0.3), it.get("lease", "ease"))
        if "pose" in it:
            e = "back" if it["pose"] in ("recoil", "tilt") else "ease"
            spine.go(t, Vector(POSTURES[it["pose"]]), it.get("pdur", 0.35), e)
        if "hands" in it:
            hl, hr = it["hands"]
            if hl: handL.go(t, hl, it.get("hdur", 0.35), "ease")
            if hr: handR.go(t, hr, it.get("hdur", 0.35), "ease")
        if "gaze" in it:
            gaze.go(t, Vector((-0.0025, -0.0015)) if it["gaze"] == "lens" else Vector((0, 0)), 0.25)
        do = it.get("do")
        if do == "type":
            tt = t + 0.1
            while tt < until - 0.08:
                for tr, off in ((offL, Vector((0.012, 0.01, 0.022))), (offR, Vector((-0.010, 0.012, 0.022)))):
                    tr.go(tt, off, 0.035, "out"); tr.key(tt + 0.07, Vector((0, 0, 0)), "in")
                    tt += 0.075
        elif do in ("tap", "tap_r"):
            tr = offL if do == "tap" else offR
            tr.go(t - 0.06, Vector((0.0, 0.01, 0.035)), 0.05, "out")
            tr.key(t, Vector((0.0, 0.0, -0.004)), "snap")
            tr.key(t + 0.14, Vector((0, 0, 0)), "ease")
        elif do == "click":
            offR.go(t - 0.04, Vector((0, 0, 0)), 0.01, "linear")
            offR.key(t, Vector((0.012, 0.0, -0.012)), "snap")
            offR.key(t + 0.12, Vector((0, 0, 0)), "ease")
        elif do == "shake":
            head_shakes.append((t, it.get("dur", 0.6)))

    def hshake(t):
        r = 0.0
        for t0, d in head_shakes:
            if t0 <= t < t0 + d:
                x = (t - t0) / d
                r += 0.20 * math.sin(x * 2 * math.pi * 2.5) * (1 - x)
        return r

    hips0 = Vector((0, -0.31, 0.525))
    POSES = {
        "type": ("world", (0.07, 0.052, 0.803), (-0.15, 1, -0.05), (0, 0, -1), (0.60, 0.0, 0.25)),
        "desk": ("world", (0.20, -0.03, 0.772), (-0.1, 1, 0), (0, 0, -1), (0.62, 0.0, 0.25)),
        "lap": ("body", (0.12, 0.20, 0.095), (-0.25, 1, -0.25), (0, 0, -1), (0.55, 0.05, 0.2)),
        "face": ("head", (0.035, 0.12, -0.13), (-0.25, 0.05, 1), (0.1, -1, 0), (0.55, 0.30, 0.2)),
        "head": ("head", (0.095, 0.02, 0.07), (-0.15, -0.35, 1), (-1, 0, 0.1), (0.55, 0.10, 0.75)),
        "cheek": ("head", (0.085, 0.07, -0.04), (-0.1, 0.1, 1), (-1, 0, 0), (0.50, 0.25, 0.25)),
        "point": ("world", (0.10, 0.34, 1.02), (0, 1, 0.1), (0, 0, -1), (0.55, 0.1, 0.4)),
        "shrug": ("body", (0.30, 0.05, 0.42), (0.4, 0.3, 0.2), (0, 0, 1), (0.6, 0.0, 0.2)),
    }
    POSES_L = {"face": ("head", (0.075, 0.035, -0.135), (-0.35, 0.15, 1), (0.6, -0.8, 0), (0.55, 0.20, 0.10))}
    POSES_R = {"mouse": ("world", (-0.335, 0.03, 0.795), (0.05, 1, 0), (0, 0, -1), (-0.62, 0.0, 0.25))}
    hand_rest = {s: arm.data.bones[f"hand.{s}"].matrix_local.to_quaternion() for s in ("L", "R")}

    def body_rot(t):
        sp = spine.at(t)
        return Euler((sp.x, -sp.z, 0.0))

    def head_center(t):
        lk = look.at(t)
        sp = spine.at(t)
        v = Vector((0, 0.012, 0.695))
        v.rotate(Euler((sp.x + 0.15 * lk.x, -sp.z, 0)))
        return hips0 + v

    def pose_eval(side, name, t):
        lib = (POSES_R if side == "R" else POSES_L).get(name)
        sgn = 1 if side == "L" else -1
        if lib is None:
            sp_, p, fi, pa, po = POSES.get(name, POSES["desk"])
            p = (p[0] * sgn, p[1], p[2]); fi = (fi[0] * sgn, fi[1], fi[2]); pa = (pa[0] * sgn, pa[1], pa[2]); po = (po[0] * sgn, po[1], po[2])
        else:
            sp_, p, fi, pa, po = lib
        rot = body_rot(t)
        if sp_ == "world":
            pos = Vector(p)
        elif sp_ == "body":
            v = Vector(p); v.rotate(rot); pos = hips0 + v
        else:
            v = Vector(p)
            lk = look.at(t)
            v.rotate(Euler((rot.x + lk.x, rot.y, rot.z - lk.y)))
            pos = head_center(t) + v
        fi_v, pa_v = Vector(fi), Vector(pa)
        if sp_ != "world":
            fi_v.rotate(rot); pa_v.rotate(rot)
        rest = quat_frame((0, 0, -1), (-sgn, 0, 0))
        q = quat_frame(fi_v, pa_v) @ rest.inverted() @ hand_rest[side]
        return pos, q, hips0 + Vector(po)

    def hand_at(side, t):
        tr, off = (handL, offL) if side == "L" else (handR, offR)
        a, b, w = tr.seg(t)
        pa, qa, la = pose_eval(side, a, t)
        pb, qb, lb = pose_eval(side, b, t)
        if qa.dot(qb) < 0: qb = -qb
        return pa.lerp(pb, w) + off.at(t), qa.slerp(qb, min(1.0, max(0.0, w))), la.lerp(lb, w)

    breath = lambda t: 0.012 * math.sin(2 * math.pi * t / 3.4)
    n_open, n_wide = lip["nerd"]["open"], lip["nerd"]["wide"]
    vals = {k: [] for k in ("spine", "chest", "neck", "head", "chair")}
    hands = {"L": ([], [], []), "R": ([], [], [])}
    for f, t in zip(range(1, N_FR + 1), times):
        sp, lk = spine.at(t), look.at(t)
        o = n_open[f - 1] if f - 1 < len(n_open) else 0.0
        hs = hshake(t)
        vals["spine"].append((sp.x, sp.y, sp.z))
        vals["chest"].append((breath(t), 0.0, 0.0))
        vals["neck"].append((0.4 * lk.x, -(0.4 * (lk.y + hs)), 0.3 * lk.z))
        vals["head"].append((0.6 * lk.x + 0.035 * o, -(0.6 * (lk.y + hs)), 0.7 * lk.z))
        vals["chair"].append((0, -0.30, 0))
        for s in ("L", "R"):
            p, q, pole = hand_at(s, t)
            hands[s][0].append(tuple(p)); hands[s][1].append(tuple(q)); hands[s][2].append(tuple(pole))
    for name in ("spine", "chest", "neck", "head"):
        write_vec(arm, f'pose.bones["{name}"].rotation_euler', vals[name], 3)
    write_vec(F["chair_root"], "location", vals["chair"], 3)
    for s in ("L", "R"):
        write_vec(ctr[f"hand.{s}"], "location", hands[s][0], 3)
        write_vec(ctr[f"hand.{s}"], "rotation_quaternion", hands[s][1], 4)
        write_vec(ctr[f"elbow.{s}"], "location", hands[s][2], 3)

    blinks, tb = [], 1.7
    while tb < DUR:
        blinks.append(tb); tb += rnd.uniform(2.4, 4.2)
    blinks += extra_blinks

    def blink(t):
        m = 1.0
        for b in blinks:
            x = (t - b) * FPS
            if -1 <= x <= 3:
                m = min(m, [0.5, 0.08, 0.15, 0.55, 1.0][int(x) + 1])
        return m

    eyes, brows, mouth = N["eyes"], N["brows"], N["mouth"]
    eye_rest = [e.location.copy() for e in eyes]
    brow_rest = [b.location.copy() for b in brows]
    E_loc = [[], []]; E_scl = [[], []]; B_loc = [[], []]; B_rotv = [[], []]
    sk = {k: [] for k in ("Open", "Wide", "Smile", "Frown", "O")}
    for f, t in zip(range(1, N_FR + 1), times):
        fc = dict(zip(FACE_KEYS, face.at(t)))
        g = gaze.at(t)
        bl = blink(t)
        o = n_open[f - 1] if f - 1 < len(n_open) else 0.0
        wd = n_wide[f - 1] if f - 1 < len(n_wide) else 0.0
        for i, s in enumerate((1, -1)):
            E_loc[i].append(tuple(eye_rest[i] + Vector((g.x, 0, g.y))))
            E_scl[i].append((fc["size"], fc["size"], fc["size"] * fc["open"] * bl))
            extra = fc["lbrow"] if s == 1 else 0
            B_loc[i].append(tuple(brow_rest[i] + Vector((0, 0, fc["raise"] + extra + 0.0015 * o))))
            B_rotv[i].append((0, s * fc["inner"], 0))
        sk["Open"].append(min(1.0, o * 1.05 + 0.15 * fc["O"]))
        sk["Wide"].append(min(1.0, fc["wide"] * (0.5 + 0.6 * o) + 0.35 * wd))
        sk["Smile"].append(fc["smile"] * (1 - 0.5 * o))
        sk["Frown"].append(fc["frown"])
        sk["O"].append(fc["O"])
    for i in range(2):
        write_vec(eyes[i], "location", E_loc[i], 3)
        write_vec(eyes[i], "scale", E_scl[i], 3)
        write_vec(brows[i], "location", B_loc[i], 3)
        write_vec(brows[i], "rotation_euler", B_rotv[i], 3)
    key = mouth.data.shape_keys
    for k, v in sk.items():
        write(key, f'key_blocks["{k}"].value', -1, v)

    # ============================================================ LIGHTING (presets keyed by storyboard cues)
    PRESETS = {
        "normal": dict(sc_c=(0.62, 0.74, 1.0), sc_e=8.0, ld_c=(0.30, 0.18, 0.85), ld_e=22.0, fl_e=18.0, mk_c=(1.0, 0.75, 0.6), mk_e=2.5),
        "alarm": dict(sc_c=(1.0, 0.18, 0.16), sc_e=14.0, ld_c=(1.0, 0.10, 0.12), ld_e=30.0, fl_e=12.0, mk_c=(1.0, 0.5, 0.45), mk_e=2.5),
        "green": dict(sc_c=(0.35, 1.0, 0.55), sc_e=12.0, ld_c=(0.20, 0.80, 0.45), ld_e=26.0, fl_e=18.0, mk_c=(1.0, 0.75, 0.6), mk_e=3.0),
        "gold": dict(sc_c=(1.0, 0.62, 0.35), sc_e=18.0, ld_c=(1.0, 0.55, 0.12), ld_e=40.0, fl_e=18.0, mk_c=(1.0, 0.68, 0.30), mk_e=5.0),
        "spot": dict(sc_c=(0.62, 0.74, 1.0), sc_e=7.0, ld_c=(0.30, 0.18, 0.85), ld_e=20.0, fl_e=13.0, mk_c=(1.0, 0.68, 0.30), mk_e=6.0),
        "dim": dict(sc_c=(0.55, 0.62, 0.95), sc_e=5.0, ld_c=(0.22, 0.12, 0.60), ld_e=12.0, fl_e=9.0, mk_c=(1.0, 0.68, 0.30), mk_e=9.5),
    }
    p0 = PRESETS[SB["meta"].get("light", "normal")]
    LT = {k: Track(v) for k, v in p0.items()}
    for t, bid, it in gather(SB, A, "light"):
        P_ = PRESETS[it["preset"]]
        d = it.get("dur", 0.12 if it["preset"] in ("alarm", "gold", "green") else 0.4)
        for k, v in P_.items():
            LT[k].go(t, v, d, "snap" if d < 0.2 else "ease")
    V = {k: [tr.at(t) for t in times] for k, tr in LT.items()}
    write_vec(L["screen"].data, "color", V["sc_c"], 3)
    write(L["screen"].data, "energy", -1, V["sc_e"])
    for k in ("led_wall", "led_top"):
        write_vec(L[k].data, "color", V["ld_c"], 3)
    write(L["led_wall"].data, "energy", -1, V["ld_e"])
    write(L["fill"].data, "energy", -1, V["fl_e"])
    write_vec(L["mascot_key"].data, "color", V["mk_c"], 3)
    write(L["mascot_key"].data, "energy", -1, V["mk_e"])
    L["rim"].data.color = (0.85, 0.25, 0.75)

    # ============================================================ CAMERAS
    cams_col = bpy.data.collections.new("Cameras")
    scene.collection.children.link(cams_col)
    head_w = lambda t: arm.matrix_world @ arm.pose.bones["head"].head
    cuts = []
    for b in SB["beats"]:
        tb_ = TL_beat(TL, b["id"])
        if b.get("shot"):
            lead = b.get("cut_lead", 0.10 if tb_["kind"] == "line" else 0.0)
            cuts.append((max(0.0, tb_["start"] - lead), b["shot"], b["id"]))
        for c in b.get("cuts", []) or []:
            cuts.append((A(c.get("at"), b["id"]), c["shot"], b["id"]))
    cuts.sort(key=lambda c: c[0])
    if not cuts or cuts[0][0] > 0:
        cuts.insert(0, (0.0, "ecu_center", SB["beats"][0]["id"]))
    scene.timeline_markers.clear()
    for i, (t0, spec, bid) in enumerate(cuts):
        t1 = cuts[i + 1][0] if i + 1 < len(cuts) else DUR
        if t1 - t0 < 1.0 / FPS:
            continue
        spec = {"name": spec} if isinstance(spec, str) else dict(spec)
        sh = shot_preset(spec, t0, t1, m_pos, head_w, mascot_eye)
        punches = [(A(p.get("at"), bid), p.get("amt", 1.18)) for p in spec.get("punch", [])]
        make_cam(scene, cams_col, f"{i:02d}_{spec['name']}", sh, t0, t1, N_FR, punches)
    scene.frame_set(1)
    print("ANIMATED", len(cuts), "shots")


def TL_beat(TL, bid):
    return next(b for b in TL["beats"] if b["id"] == bid)


def scr(px, py):
    """Centre-monitor pixel (2400x1350 texture) -> world point."""
    return Vector(((px - 1200) * 0.70 / 2400, 0.47, 1.105 + (675 - py) * 0.39375 / 1350))


def shot_preset(spec, t0, t1, m_pos, head_w, mascot_eye):
    """Camera presets. Returns dict(p0, p1, tgt (Vector or fn), l0, l1, fstop, focus fn|None, shake)."""
    V = Vector
    n = spec["name"]
    m0 = m_pos.at(t0)
    if n in ("ecu_center", "monitor_ecu"):
        c = scr(1200, 640 if n == "ecu_center" else 700)
        p = c + V((0.0, -0.47 if n == "ecu_center" else -0.42, -0.02))
        d = dict(p0=p, p1=p + V((0, 0.025, 0)), tgt=c + V((0, 0, 0.085 if n == "ecu_center" else 0.03)), l0=38, l1=38, fstop=5.6)
    elif n == "ots_nerd":
        d = dict(p0=V((-0.34, -0.62, 1.62)), p1=V((-0.30, -0.54, 1.58)), tgt=V((0.14, 0.45, 1.00)), l0=28, l1=30, fstop=3.5,
                 focus=lambda t: V((0.10, 0.47, 1.06)))
    elif n in ("nerd_mcu", "nerd_cu"):
        cu = n == "nerd_cu"
        d = dict(p0=V((-0.10, 0.25 if cu else 0.27, 1.02 if cu else 1.00)), p1=V((-0.09, 0.20 if cu else 0.23, 1.04 if cu else 1.00)),
                 tgt=lambda t: head_w(t) + V((0, 0, -0.05 if cu else -0.07)), l0=38 if cu else 32, l1=42 if cu else 35, fstop=2.8,
                 focus=lambda t: head_w(t) + V((0, 0.09, 0)))
    elif n == "claude_cu":
        d = dict(p0=m0 + V((0.11, -0.52, 0.17)), p1=m0 + V((0.10, -0.48, 0.165)), tgt=lambda t: mascot_eye(t) + V((-0.01, 0, -0.015)),
                 l0=42, l1=44, fstop=2.4, focus=lambda t: mascot_eye(t) + V((0, -0.06, -0.01)))
    elif n in ("claude_lens", "claude_lens_close"):
        edge = m0
        lp = CAM_LESSON + (edge - CAM_LESSON) * 0.30
        if n == "claude_lens":
            d = dict(p0=CAM_LESSON, p1=lp, tgt=lambda t: mascot_eye(t) + V((-0.04, 0.02, 0.0)), l0=34, l1=36, fstop=2.4, focus=mascot_eye)
        else:
            d = dict(p0=lp, p1=CAM_LESSON + (edge - CAM_LESSON) * 0.45, tgt=mascot_eye, l0=40, l1=44, fstop=2.2, focus=mascot_eye)
    elif n == "wide_monitors":
        d = dict(p0=V((0.62, -0.42, 1.22)), p1=V((0.58, -0.36, 1.20)), tgt=V((0.02, 0.42, 1.02)), l0=22, l1=23, fstop=4.0,
                 focus=lambda t: V((0.10, 0.40, 1.02)))
    elif n == "two_shot":
        d = dict(p0=V((0.92, -0.78, 1.28)), p1=V((0.88, -0.72, 1.27)), tgt=V((0.16, 0.0, 0.98)), l0=26, l1=27, fstop=4.0,
                 focus=lambda t: V((0.16, -0.05, 1.0)))
    elif n == "left_mon":
        d = dict(p0=V((0.56, -0.40, 1.00)), p1=V((0.53, -0.35, 1.00)), tgt=V((0.02, 0.30, 0.97)), l0=24, l1=25, fstop=3.2,
                 focus=lambda t: mascot_eye(t))
    elif n == "right_mon":
        d = dict(p0=V((-0.20, -0.10, 1.00)), p1=V((-0.17, -0.07, 1.00)), tgt=V((0.55, 0.30, 0.98)), l0=28, l1=29, fstop=3.2,
                 focus=lambda t: mascot_eye(t))
    elif n == "center_push":
        d = dict(p0=V((0.40, -0.30, 1.08)), p1=V((0.37, -0.25, 1.07)), tgt=V((0.06, 0.47, 1.02)), l0=24, l1=26, fstop=3.6,
                 focus=lambda t: V((0.12, 0.42, 1.0)))
    elif n == "title":
        d = dict(p0=CAM_LESSON, p1=CAM_LESSON, tgt=V((0.27, 0.2, 0.9)), l0=30, l1=30, fstop=1.6)
    else:
        raise KeyError(f"unknown shot preset {n}")
    if "lens" in spec:
        d["l0"], d["l1"] = spec["lens"], spec.get("lens_end", spec["lens"] * d["l1"] / d["l0"])
    if spec.get("tgt_off"):                      # re-frame: positive z puts the subject lower in the frame
        off, base = Vector(spec["tgt_off"]), d["tgt"]
        d["tgt"] = (lambda t, b=base: b(t) + off) if callable(base) else Vector(base) + off
    if spec.get("pos_off"):
        d["p0"] = Vector(d["p0"]) + Vector(spec["pos_off"]); d["p1"] = Vector(d["p1"]) + Vector(spec["pos_off"])
    if spec.get("static"):
        d["p1"] = d["p0"]; d["l1"] = d["l0"]
    d["shake"] = spec.get("shake", 0.0)
    return d


def make_cam(scene, coll, name, sh, t0, t1, N_FR, punches):
    cd = bpy.data.cameras.new("CAM_" + name)
    cd.sensor_fit = "HORIZONTAL"; cd.sensor_width = 36
    cd.clip_start = 0.01; cd.clip_end = 40
    cd.dof.use_dof = True; cd.dof.aperture_blades = 7
    cam = bpy.data.objects.new("CAM_" + name, cd)
    coll.objects.link(cam)
    cam.rotation_mode = "QUATERNION"
    fa, fb = max(1, fr(t0) - 2), min(N_FR, fr(t1) + 2)
    locs, quats, lens, focus, fst = [], [], [], [], []
    prevq = None
    dyn = callable(sh["tgt"]) or callable(sh.get("focus"))
    for f in range(fa, fb + 1):
        t = tm(f)
        if dyn:
            scene.frame_set(f)
        w = EASE["ease"](min(1, max(0, (t - t0) / max(1e-3, t1 - t0))))
        pos = Vector(sh["p0"]).lerp(Vector(sh["p1"]), w)
        if sh["shake"]:
            pos = pos + Vector((math.sin(t * 7.1) * sh["shake"], 0, math.sin(t * 5.3 + 1) * sh["shake"] * 0.6))
        tgt = sh["tgt"](t) if callable(sh["tgt"]) else Vector(sh["tgt"])
        q = (tgt - pos).to_track_quat("-Z", "Y")
        if prevq is not None and prevq.dot(q) < 0:
            q = -q
        prevq = q
        ln = sh["l0"] + (sh["l1"] - sh["l0"]) * w
        for tp, amt in punches:                     # quick zoom punch on a word (pattern interrupt)
            if t >= tp - 0.02:
                x = t - tp
                k = EASE["snap"](min(1, max(0, (x + 0.02) / 0.07)))
                ln *= 1 + (amt - 1) * k
        locs.append(tuple(pos)); quats.append(tuple(q)); lens.append(ln)
        fp = sh["focus"](t) if callable(sh.get("focus")) else tgt
        focus.append((fp - pos).length)
        fst.append(sh.get("fstop", 2.8))
    write_vec(cam, "location", locs, 3, f0=fa)
    write_vec(cam, "rotation_quaternion", quats, 4, f0=fa)
    write(cd, "lens", -1, lens, f0=fa)
    write(cd, "dof.focus_distance", -1, focus, f0=fa)
    write(cd, "dof.aperture_fstop", -1, fst, f0=fa)
    m = scene.timeline_markers.new("S_" + name, frame=fr(t0))
    m.camera = cam
    if t0 <= 0:
        scene.camera = cam
