import tkinter as tk
import tkinter.font as tkfont
import random
import math

# ==========================================================
# Rialo 动态文字爱心
#
# 文字布局：
#   外围只使用「我爱你」和「Love You」，沿着爱心边缘组成空心爱心
#   中央只显示「Love You Rialo」
#
# 可调整参数集中在下方，方便后续修改。
# ==========================================================

BG = "#000000"
CENTER_TEXT = "Love You Rialo"
EDGE_WORDS = ("我爱你", "Love You")

# 爱心整体大小：相对于窗口
HEART_WIDTH_RATIO = 0.88
HEART_HEIGHT_RATIO = 0.88

# 内层留白比例。数值越大，文字边框越薄；越小，边框越厚
INNER_HEART_SCALE = 0.79

# 文字颜色和字号范围
TEXT_COLORS = (
    "#ff82ad", "#ed8acb", "#bd96ff",
    "#7fcfff", "#83dfb8", "#ffd08a"
)
MIN_WORD_SIZE = 9
MAX_WORD_SIZE = 15
ROW_GAP = 15
WORD_GAP = 3

# 漂浮小爱心数量
PARTICLE_COUNT = 28

# 动画间隔单位是毫秒：数值越大，动作越慢。
# 外围每个文字片段间隔 220 毫秒。
BUILD_INTERVAL_MS = 220

# 中央手写笔迹每个细分笔段间隔 50 毫秒。
STROKE_INTERVAL_MS = 50


def cubic_bezier(p0, p1, p2, p3, t):
    """三次贝塞尔曲线采样。"""
    u = 1.0 - t
    return (
        u**3 * p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
        u**3 * p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1],
    )


def heart_curve_points(steps_per_curve=420):
    """经典对称爱心：圆润双心瓣、明确凹口、自然尖底。"""
    notch = (0.0, -0.34)
    right_lobe = (0.53, -0.31)
    tip = (0.0, 0.56)
    curves = [
        # 中央凹口 -> 右侧圆润心瓣顶部 -> 右侧外轮廓 -> 底部尖端
        (notch, (0.15, -0.57), (0.48, -0.58), right_lobe),
        (right_lobe, (0.69, -0.04), (0.38, 0.31), tip),
        # 底部尖端 -> 左侧外轮廓 -> 左侧圆润心瓣 -> 中央凹口
        (tip, (-0.38, 0.31), (-0.69, -0.04), (-0.53, -0.31)),
        ((-0.53, -0.31), (-0.48, -0.58), (-0.15, -0.57), notch),
    ]
    points = []
    for curve in curves:
        for i in range(steps_per_curve):
            points.append(cubic_bezier(*curve, i / steps_per_curve))
    return points


def build_heart_polygon(cx, cy, width, height, scale=1.0, steps=1400):
    """由平滑贝塞尔爱心曲线生成多边形；缩放内层时保持同心对称。"""
    raw = heart_curve_points(max(100, steps // 4))
    result = []
    for x, y in raw:
        px = cx + x * width * scale
        py = cy + y * height * scale
        result.append((px, py))
    return result


def horizontal_intersections(poly, y):
    """求水平扫描线与多边形边界的交点。"""
    xs = []
    for i, (x1, y1) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 <= y < y2) or (y2 <= y < y1):
            if abs(y2 - y1) > 1e-9:
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    return sorted(xs)


def polygon_intervals(poly, y):
    xs = horizontal_intersections(poly, y)
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


def subtract_intervals(outer_intervals, inner_intervals):
    """从外层心形扫描区间中扣除内层心形，得到空心边框区域。"""
    result = []
    for left, right in outer_intervals:
        pieces = [(left, right)]
        for cut_left, cut_right in inner_intervals:
            next_pieces = []
            for a, b in pieces:
                if cut_right <= a or cut_left >= b:
                    next_pieces.append((a, b))
                else:
                    if cut_left > a:
                        next_pieces.append((a, cut_left))
                    if cut_right < b:
                        next_pieces.append((cut_right, b))
            pieces = next_pieces
        result.extend((a, b) for a, b in pieces if b - a > 2)
    return result


class RialoHeart:
    def __init__(self, root):
        self.root = root
        self.root.title("Love You Rialo")
        self.root.configure(bg=BG)
        self.root.geometry("1180x820")
        self.root.minsize(760, 560)

        self.canvas = tk.Canvas(
            root, bg=BG, highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        self.width = 1180
        self.height = 820
        self.last_size = None
        self.text_items = []
        self.particles = []
        self.frame = 0
        self.animation_job = None
        self.build_job = None
        self.build_items = []
        self.build_positions = {}
        self.build_item_index = 0
        self.center_items = []
        self.center_char_index = 0
        self.center_stroke_segments = []
        self.center_stroke_index = 0
        self.font_cache = {}

        self.canvas.bind("<Configure>", self.on_resize)
        self.root.bind("<Escape>", lambda event: self.close())
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def on_resize(self, event):
        if event.width < 100 or event.height < 100:
            return
        new_size = (event.width, event.height)
        if new_size != self.last_size:
            self.width, self.height = new_size
            self.last_size = new_size
            self.draw_scene()

    def font_for(self, text, size):
        family = "Microsoft YaHei" if any(ord(c) > 127 for c in text) else "Arial"
        key = (family, int(size))
        if key not in self.font_cache:
            self.font_cache[key] = tkfont.Font(
                family=family, size=int(size), weight="bold"
            )
        return self.font_cache[key]

    def title_font(self):
        size = int(min(self.height * 0.075, self.width * 0.065, 62))
        max_width = self.width * 0.49
        font = tkfont.Font(family="Arial", size=size, weight="bold")
        while font.measure(CENTER_TEXT) > max_width and size > 20:
            size -= 1
            font.configure(size=size)
        return font

    def add_words_to_interval(self, left, right, y, row_index, rng):
        """在每条心形边框扫描区间内自适应排字，窄处自动缩小字号。"""
        pad = 1
        left += pad
        right -= pad
        available = right - left
        if available < 19:
            return

        words = ["我爱你", "Love You"]
        pieces = []
        used = 0
        index = row_index % 2

        # 先用正常字号填充；遇到窄区间时逐级缩小，避免整段被跳过
        while available - used >= 16 and len(pieces) < 80:
            chosen = None
            for size in range(rng.randint(11, 14), 8, -1):
                for shift in (0, 1):
                    word = words[(index + shift) % 2]
                    font = self.font_for(word, size)
                    width = font.measure(word)
                    if used + width <= available:
                        chosen = (word, font, rng.choice(TEXT_COLORS), width)
                        index += shift
                        break
                if chosen:
                    break

            if not chosen:
                break

            pieces.append(chosen)
            used += chosen[3] + WORD_GAP
            index += 1

        if not pieces:
            # 极窄位置尽量保留一个小号中文词，帮助轮廓不断开
            for size in range(9, 6, -1):
                word = "我爱你"
                font = self.font_for(word, size)
                width = font.measure(word)
                if width <= available:
                    pieces.append((word, font, rng.choice(TEXT_COLORS), width))
                    used = width
                    break

        if not pieces:
            return

        total = sum(p[3] for p in pieces) + WORD_GAP * (len(pieces) - 1)
        x = left + max(0, (available - total) / 2)
        for word, font, color, width in pieces:
            item = self.canvas.create_text(
                x, y, text=word, anchor="w", fill=color, font=font,
                state="hidden"
            )
            phase = rng.uniform(0, math.tau)
            self.text_items.append((item, x, y, phase))
            self.build_positions[item] = (x + width / 2, y)
            self.current_build_row.append(item)
            x += width + WORD_GAP

    def draw_outline_words(self):
        """用同一组内外心形边界生成连续的空心文字带。"""
        cx = self.width / 2
        cy = self.height * 0.50

        heart_w = min(self.width * HEART_WIDTH_RATIO, self.height * 1.15)
        heart_h = min(self.height * HEART_HEIGHT_RATIO, self.width * 0.95)

        outer = build_heart_polygon(cx, cy, heart_w, heart_h, 1.0, steps=2400)
        inner = build_heart_polygon(
            cx, cy, heart_w, heart_h, INNER_HEART_SCALE, steps=2400
        )

        outer_top = min(y for _, y in outer)
        outer_bottom = max(y for _, y in outer)
        inner_top = min(y for _, y in inner)
        inner_bottom = max(y for _, y in inner)

        title_font = self.title_font()
        title_width = title_font.measure(CENTER_TEXT)
        title_height = title_font.metrics("linespace")
        title_box = (
            cx - title_width / 2 - 12,
            cy - title_height / 2 - 5,
            cx + title_width / 2 + 12,
            cy + title_height / 2 + 5
        )

        # 密集扫描整颗心形边框，避免行距过大造成视觉断层
        row_gap = ROW_GAP
        rng = random.Random(20261118)
        y = outer_top + 2
        row_index = 0

        while y <= outer_bottom - 1:
            self.current_build_row = []
            outer_intervals = polygon_intervals(outer, y)
            inner_intervals = (
                polygon_intervals(inner, y)
                if inner_top <= y <= inner_bottom else []
            )
            ring_intervals = subtract_intervals(
                outer_intervals, inner_intervals
            )

            safe_intervals = []
            for left, right in ring_intervals:
                if title_box[1] <= y <= title_box[3]:
                    if left < title_box[0] - 4:
                        safe_intervals.append((left, min(right, title_box[0] - 4)))
                    if right > title_box[2] + 4:
                        safe_intervals.append((max(left, title_box[2] + 4), right))
                else:
                    safe_intervals.append((left, right))

            for left, right in safe_intervals:
                self.add_words_to_interval(left, right, y, row_index, rng)

            if self.current_build_row:
                self.build_items.extend(self.current_build_row)
            y += row_gap
            row_index += 1

        # 从爱心上方中央的凹口开始，按距离向两侧和下方扩散。
        start_x = cx
        start_y = cy - heart_h * 0.34
        self.build_items.sort(
            key=lambda item: math.hypot(
                (self.build_positions[item][0] - start_x) / heart_w,
                (self.build_positions[item][1] - start_y) / heart_h
            )
        )

    def draw_center(self):
        """准备中央标题的单线笔画路径，按书写顺序逐段绘制。"""
        font = self.title_font()
        size = font.cget("size")
        total_width = font.measure(CENTER_TEXT)
        x_cursor = self.width / 2 - total_width / 2
        center_y = self.height * 0.50
        top_y = center_y - size * 0.48
        glyph_height = size * 0.88
        line_width = max(2, int(size * 0.065))

        # 每个字母使用简化的连续线稿路径；坐标范围约为 0～1。
        # 一条路径代表一笔，按路径顺序逐段写出。
        glyphs = {
            "L": [[(0.12, 0.04), (0.12, 0.98), (0.92, 0.98)]],
            "o": [[(0.88, 0.52), (0.82, 0.25), (0.62, 0.08), (0.35, 0.06), (0.13, 0.24), (0.08, 0.53), (0.14, 0.82), (0.36, 0.96), (0.63, 0.94), (0.83, 0.76), (0.88, 0.52)]],
            "v": [[(0.08, 0.10), (0.48, 0.96), (0.90, 0.10)]],
            "e": [[(0.10, 0.55), (0.84, 0.55), (0.82, 0.34), (0.67, 0.14), (0.43, 0.07), (0.20, 0.20), (0.08, 0.48), (0.11, 0.73), (0.29, 0.91), (0.57, 0.97), (0.82, 0.84)]],
            "Y": [[(0.08, 0.05), (0.49, 0.48), (0.92, 0.05)], [(0.49, 0.48), (0.49, 0.98)]],
            "u": [[(0.10, 0.10), (0.10, 0.67), (0.18, 0.88), (0.39, 0.97), (0.65, 0.91), (0.88, 0.72), (0.88, 0.10)]],
            "R": [[(0.13, 0.98), (0.13, 0.05), (0.57, 0.05), (0.82, 0.16), (0.88, 0.34), (0.80, 0.49), (0.58, 0.55), (0.13, 0.55)], [(0.52, 0.55), (0.92, 0.98)]],
            "i": [[(0.48, 0.34), (0.48, 0.98)], [(0.48, 0.08), (0.48, 0.10)]],
            "a": [[(0.84, 0.34), (0.66, 0.12), (0.40, 0.07), (0.17, 0.20), (0.08, 0.49), (0.13, 0.77), (0.34, 0.95), (0.61, 0.94), (0.84, 0.75), (0.84, 0.34)], [(0.84, 0.34), (0.84, 0.98)]],
            "l": [[(0.50, 0.03), (0.50, 0.98)]],
        }

        self.center_stroke_segments.clear()
        self.center_stroke_index = 0
        for char in CENTER_TEXT:
            char_width = font.measure(char)
            if char != " ":
                paths = glyphs.get(char, [])
                # 字形在自己的字宽内按比例绘制
                for path in paths:
                    points = [
                        (x_cursor + px * char_width, top_y + py * glyph_height)
                        for px, py in path
                    ]
                    for p1, p2 in zip(points, points[1:]):
                        # 将每段细分，让笔迹看起来是连续写出来的
                        subdivisions = 4
                        for step in range(1, subdivisions + 1):
                            t0 = (step - 1) / subdivisions
                            t1 = step / subdivisions
                            a = (p1[0] + (p2[0] - p1[0]) * t0,
                                 p1[1] + (p2[1] - p1[1]) * t0)
                            b = (p1[0] + (p2[0] - p1[0]) * t1,
                                 p1[1] + (p2[1] - p1[1]) * t1)
                            self.center_stroke_segments.append((a, b, line_width))
            x_cursor += char_width

        # 小粉心作为标题点缀，等中央标题完整写完后再显示
        self.canvas.create_text(
            self.width * 0.72,
            self.height * 0.455,
            text="♥",
            fill="#ff78a8",
            font=("Arial", 13, "bold"),
            state="hidden",
            tags=("center_decoration",)
        )

    def draw_particles(self):
        rng = random.Random(814)
        count = max(PARTICLE_COUNT, int(self.width * self.height / 30000))

        for _ in range(count):
            x = rng.uniform(12, self.width - 12)
            y = rng.uniform(12, self.height - 12)
            size = rng.choice((8, 10, 12, 15, 18))
            item = self.canvas.create_text(
                x, y, text="♥",
                fill=rng.choice(("#ff5f96", "#ff78a8", "#ff91bd")),
                font=("Arial", size, "bold")
            )
            self.particles.append({
                "id": item,
                "x": x,
                "y": y,
                "speed": rng.uniform(0.25, 0.75),
                "phase": rng.uniform(0, math.tau),
                "drift": rng.uniform(0.12, 0.36)
            })

    def draw_scene(self):
        # 窗口尺寸变化或重绘时，先取消上一轮构建和动画
        for job_name in ("animation_job", "build_job"):
            job = getattr(self, job_name)
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, job_name, None)

        self.canvas.delete("all")
        self.text_items.clear()
        self.particles.clear()
        self.build_items.clear()
        self.build_positions.clear()
        self.build_item_index = 0
        self.center_items.clear()
        self.center_char_index = 0
        self.center_stroke_segments.clear()
        self.center_stroke_index = 0

        self.draw_outline_words()
        self.draw_center()

        # 从爱心上方中央凹口附近开始，逐个文字片段向外拼出外围爱心
        self.build_job = self.root.after(250, self.reveal_next_rows)

    def reveal_next_rows(self):
        """每隔 BUILD_INTERVAL_MS 毫秒显示一个文字片段，让爱心慢慢编织出来。"""
        self.build_job = None

        if self.build_item_index < len(self.build_items):
            item = self.build_items[self.build_item_index]
            self.canvas.itemconfigure(item, state="normal")
            self.build_item_index += 1

            self.build_job = self.root.after(
                BUILD_INTERVAL_MS, self.reveal_next_rows
            )
            return

        # 外围爱心拼完后，开始让中央标题一个字一个字出现
        self.reveal_next_center_char()

    def reveal_next_center_char(self):
        """每隔 STROKE_INTERVAL_MS 毫秒绘制一小段中央手写笔迹。"""
        self.build_job = None

        if self.center_stroke_index < len(self.center_stroke_segments):
            (x1, y1), (x2, y2), line_width = self.center_stroke_segments[self.center_stroke_index]
            self.canvas.create_line(
                x1, y1, x2, y2,
                fill="#ff78a8",
                width=line_width,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                smooth=True
            )
            self.center_stroke_index += 1
            self.build_job = self.root.after(
                STROKE_INTERVAL_MS, self.reveal_next_center_char
            )
            return

        # 中央标题全部写完后，再显示装饰和漂浮爱心
        self.canvas.itemconfigure("center_decoration", state="normal")
        self.draw_particles()
        self.animate()

    def close(self):
        """关闭窗口前取消动画回调，避免退出时残留 after 任务。"""
        for job_name in ("animation_job", "build_job"):
            job = getattr(self, job_name)
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, job_name, None)
        self.root.destroy()

    def animate(self):
        self.frame += 1

        # 文字只做非常轻微的上下浮动，整体爱心轮廓保持稳定
        for item, x, y, phase in self.text_items:
            offset = math.sin(self.frame * 0.018 + phase) * 0.28
            self.canvas.coords(item, x, y + offset)

        # 粉色小爱心缓慢上升并轻微左右漂动
        for particle in self.particles:
            particle["y"] -= particle["speed"]
            particle["x"] += (
                math.sin(self.frame * 0.015 + particle["phase"])
                * particle["drift"]
            )
            if particle["y"] < -22:
                particle["y"] = self.height + 18
                particle["x"] = random.uniform(12, self.width - 12)
            self.canvas.coords(
                particle["id"], particle["x"], particle["y"]
            )

        self.animation_job = self.root.after(33, self.animate)


def main():
    root = tk.Tk()
    RialoHeart(root)
    root.mainloop()


if __name__ == "__main__":
    main()
