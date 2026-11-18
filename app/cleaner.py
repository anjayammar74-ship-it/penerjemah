"""Erase English letters from bubbles and compute where Indonesian text should sit."""
import numpy as np
from scipy import ndimage


def _mode_color(px: np.ndarray) -> np.ndarray:
    if px.size == 0:
        return np.array([255, 255, 255])
    flat = px.reshape(-1, 3)
    q = (flat // 16).astype(np.int32)
    keys = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    mode = np.bincount(keys).argmax()
    return flat[keys == mode].mean(axis=0)


def _hex(c) -> str:
    r, g, b = (int(max(0, min(255, v))) for v in c)
    return f"#{r:02x}{g:02x}{b:02x}"


def _clip(b, W, H):
    x0, y0, x1, y1 = b
    return [int(max(0, min(W, x0))), int(max(0, min(H, y0))), int(max(0, min(W, x1))), int(max(0, min(H, y1)))]


def clean_bubble(arr: np.ndarray, text_box, bubble_box, shape: str):
    """Mutates arr (H,W,3 uint8). Returns placement dict in pixels."""
    H, W = arr.shape[:2]
    tx0, ty0, tx1, ty1 = _clip(text_box, W, H)
    if tx1 - tx0 < 4 or ty1 - ty0 < 4:
        return None
    bx0, by0, bx1, by1 = _clip(bubble_box or text_box, W, H)
    # bubble must contain the text box
    bx0, by0, bx1, by1 = min(bx0, tx0), min(by0, ty0), max(bx1, tx1), max(by1, ty1)

    bg = _mode_color(arr[ty0:ty1, tx0:tx1])
    region = arr[ty0:ty1, tx0:tx1].astype(np.int16)
    diff = np.abs(region - bg).max(axis=2)
    clean_share = float((diff < 40).mean())
    lum = lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    light = lum(bg) > 128
    ink_px = region[diff > 90].reshape(-1, 3)
    fg = np.array([20, 20, 20]) if light else np.array([250, 250, 250])
    if len(ink_px) > 30:
        order = np.argsort(ink_px.sum(axis=1))
        core_ink = ink_px[order[: max(5, len(order) // 5)]] if light else ink_px[order[-max(5, len(order) // 5):]]
        c = np.median(core_ink, axis=0)
        if (c.max() - c.min()) > 60 and abs(lum(c) - lum(bg)) > 110:
            fg = c  # genuinely coloured lettering
    rows = (diff > 90).mean(axis=1) > 0.02
    runs = int(np.count_nonzero(rows[1:] & ~rows[:-1]) + (1 if rows[:1].any() else 0))
    lines = max(1, runs)
    font_px = (ty1 - ty0) / lines * 0.78
    uniform = clean_share > 0.5
    if uniform:
        tw, th = tx1 - tx0, ty1 - ty0
        wx0, wy0, wx1, wy1 = _clip([tx0 - 2 * tw, ty0 - 4 * th, tx1 + 2 * tw, ty1 + 4 * th], W, H)
        win = arr[wy0:wy1, wx0:wx1]
        d = np.abs(win.astype(np.int16) - bg).max(axis=2)
        ink = d >= 50
        sealed = ndimage.binary_dilation(ink, structure=np.ones((3, 3)), iterations=3)
        lab, n = ndimage.label(~sealed)
        wh, ww = d.shape
        cy0, cy1, cx0, cx1 = ty0 - wy0, ty1 - wy0, tx0 - wx0, tx1 - wx0
        rim = np.concatenate([lab[cy0:cy1, max(0, cx0 - 2)], lab[cy0:cy1, min(ww - 1, cx1 + 1)],
                              lab[max(0, cy0 - 2), cx0:cx1], lab[min(wh - 1, cy1 + 1), cx0:cx1],
                              lab[cy0:cy1, cx0:cx1].ravel()])
        rim = rim[rim > 0]
        rid = int(np.bincount(rim).argmax()) if len(rim) else 0
        region = lab == rid if rid else np.zeros_like(ink)
        ys, xs = np.where(region) if rid else (np.array([0]), np.array([0]))
        closed = bool(rid) and ys.min() > 0 and xs.min() > 0 and ys.max() < wh - 1 and xs.max() < ww - 1
        if closed and (ys.max() - ys.min()) * (xs.max() - xs.min()) > 40 * tw * th:
            closed = False

        def near(mx, my):
            m = np.zeros_like(ink)
            m[max(0, int(cy0 - my)):int(cy1 + my), max(0, int(cx0 - mx)):int(cx1 + mx)] = True
            return m

        def letter_marks():
            zone = near(0.12 * tw + 5, 0.35 * th + 5)
            marks = (d > 40) & zone
            lab2, _ = ndimage.label(marks, structure=np.ones((3, 3)))
            zy, zx = np.where(zone)
            zy0, zy1, zx0, zx1 = zy.min(), zy.max(), zx.min(), zx.max()
            em = np.zeros_like(ink)
            for i, sl in enumerate(ndimage.find_objects(lab2)):
                if sl is None:
                    continue
                inside = sl[0].start > zy0 and sl[0].stop - 1 < zy1 and sl[1].start > zx0 and sl[1].stop - 1 < zx1
                if inside:  # letters sit fully inside; artwork crossing the zone edge is left alone
                    em[sl] |= lab2[sl] == i + 1
            return ndimage.binary_dilation(em, iterations=3) & (d > 4)

        if closed:
            interior = ndimage.binary_dilation(ndimage.binary_fill_holes(region), structure=np.ones((3, 3)), iterations=2)
            # letters glued to the bubble outline are not part of the interior: wipe them as marks too
            erase = (interior & near(0.3 * tw + 8, 0.8 * th + 8)) | letter_marks()
            ry0, ry1, rx0, rx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        else:
            erase = letter_marks()
            ry0, ry1, rx0, rx1 = cy0, cy1, cx0, cx1
        win[erase] = bg.astype(np.uint8)
        core = win[cy0:cy1, cx0:cx1]
        # flatten the faint halo left around letters, but never paint over the art next to the bubble
        near_bg = np.abs(core.astype(np.int16) - bg).max(axis=2) < (70 if closed else 40)
        if closed:
            near_bg &= erase[cy0:cy1, cx0:cx1]
        core[near_bg] = bg.astype(np.uint8)
        bx0, by0, bx1, by1 = wx0 + rx0, wy0 + ry0, wx0 + rx1, wy0 + ry1
        if closed:
            k = 0.15 if shape in ("ellipse", "cloud") else 0.05
            ix0, ix1 = bx0 + (bx1 - bx0) * k, bx1 - (bx1 - bx0) * k
            iy0, iy1 = by0 + (by1 - by0) * (k + 0.03), by1 - (by1 - by0) * (k + 0.03)
            # stay close to where the English sat, but use free bubble space around it
            gx, gy = max(0.35 * tw, 2.5 * font_px), max(0.5 * th, 1.4 * font_px)
            px0, px1 = min(tx0, max(ix0, tx0 - gx)), max(tx1, min(ix1, tx1 + gx))
            py0, py1 = min(ty0, max(iy0, ty0 - gy)), max(ty1, min(iy1, ty1 + gy))
        else:
            gx, gy = max(0.08 * tw, 1.0 * font_px), max(0.15 * th, 0.6 * font_px)
            px0, px1, py0, py1 = tx0 - gx, tx1 + gx, ty0 - gy, ty1 + gy
        mode = "clean"
    else:
        # text over artwork: paint a soft patch behind the text
        pad = max(6, int((ty1 - ty0) * 0.12))
        x0, y0, x1, y1 = _clip([tx0 - pad, ty0 - pad, tx1 + pad, ty1 + pad], W, H)
        patch = arr[y0:y1, x0:x1].astype(np.float32)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        fx = np.minimum(xx - x0, x1 - 1 - xx) / max(1, pad)
        fy = np.minimum(yy - y0, y1 - 1 - yy) / max(1, pad)
        alpha = np.clip(np.minimum(fx, fy), 0, 1)[..., None]
        arr[y0:y1, x0:x1] = (patch * (1 - alpha) + bg * alpha).astype(np.uint8)
        px0, py0, px1, py1 = x0 + pad * 0.4, y0 + pad * 0.4, x1 - pad * 0.4, y1 - pad * 0.4
        mode = "patch"
    return {"x0": px0, "y0": py0, "x1": px1, "y1": py1, "bg": _hex(bg), "fg": _hex(fg), "mode": mode, "font_px": float(font_px)}


def bubble_region(arr: np.ndarray, text_box) -> list[float] | None:
    """Box around ALL lettering of the bubble that contains text_box (so a half-read bubble gets re-read whole)."""
    H, W = arr.shape[:2]
    tx0, ty0, tx1, ty1 = _clip(text_box, W, H)
    if tx1 - tx0 < 3 or ty1 - ty0 < 3:
        return None
    bg = _mode_color(arr[ty0:ty1, tx0:tx1])
    tw, th = tx1 - tx0, ty1 - ty0
    wx0, wy0, wx1, wy1 = _clip([tx0 - 3 * tw - 120, ty0 - 5 * th - 160, tx1 + 3 * tw + 120, ty1 + 5 * th + 160], W, H)
    win = arr[wy0:wy1, wx0:wx1]
    d = np.abs(win.astype(np.int16) - bg).max(axis=2)
    ink = d >= 50
    sealed = ndimage.binary_dilation(ink, structure=np.ones((3, 3)), iterations=3)
    lab, _ = ndimage.label(~sealed)
    cy0, cy1, cx0, cx1 = ty0 - wy0, ty1 - wy0, tx0 - wx0, tx1 - wx0
    wh, ww = d.shape
    rim = np.concatenate([lab[cy0:cy1, max(0, cx0 - 2)], lab[cy0:cy1, min(ww - 1, cx1 + 1)],
                          lab[max(0, cy0 - 2), cx0:cx1], lab[min(wh - 1, cy1 + 1), cx0:cx1]])
    rim = rim[rim > 0]
    if not len(rim):
        return [tx0, ty0, tx1, ty1]
    region = lab == int(np.bincount(rim).argmax())
    ys, xs = np.where(region)
    closed = ys.min() > 0 and xs.min() > 0 and ys.max() < wh - 1 and xs.max() < ww - 1
    rh, rw = ys.max() - ys.min(), xs.max() - xs.min()
    if not closed or rh * rw > max(40 * tw * th, 150000) or rh > 800:
        return [tx0, ty0, tx1, ty1]
    letters = ndimage.binary_fill_holes(region) & ~region & ink
    ly, lx = np.where(letters)
    if not len(ly):
        return [tx0, ty0, tx1, ty1]
    return [float(min(tx0, wx0 + lx.min())), float(min(ty0, wy0 + ly.min())),
            float(max(tx1, wx0 + lx.max() + 1)), float(max(ty1, wy0 + ly.max() + 1))]
