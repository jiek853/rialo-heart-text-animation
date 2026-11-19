# 动态文字爱心 · Love You Rialo

纯 Python + Tkinter 写的动画爱心。

- 外围：用「我爱你」和「Love You」两种文字，沿着心形轮廓自适应排字，拼成一颗**空心**爱心
- 中央：一笔一笔“写”出 `Love You Rialo`
- 结尾：粉色小爱心缓缓上浮

无第三方依赖，只用 Python 标准库。

## 运行

```bash
python rialo_heart_curve_outer_220ms_top_center_start.py
```

需要 Python 3.8 或更高版本（Windows / macOS / Linux 均可，需带 tkinter）。

按 `Esc` 或关闭窗口退出。

## 效果

1. 从爱心上方中央的凹口开始，外围文字一片一片向外扩散，把爱心“编织”出来（每个片段间隔 220 ms）
2. 外围完成后，中央标题开始逐段手写（每笔段间隔 50 ms）
3. 标题写完后，装饰小爱心与漂浮爱心出现

## 可调参数

脚本开头的常量集中控制效果，改完直接运行即可：

| 参数 | 默认值 | 作用 |
| --- | --- | --- |
| `BG` | `#000000` | 背景色 |
| `CENTER_TEXT` | `Love You Rialo` | 中央标题文字 |
| `EDGE_WORDS` | `我爱你` / `Love You` | 外围轮廓使用的词 |
| `HEART_WIDTH_RATIO` | `0.88` | 爱心宽度占窗口比例 |
| `HEART_HEIGHT_RATIO` | `0.88` | 爱心高度占窗口比例 |
| `INNER_HEART_SCALE` | `0.79` | 内层心形缩放；越大边框越薄 |
| `TEXT_COLORS` | 6 色 | 文字配色循环 |
| `MIN_WORD_SIZE` / `MAX_WORD_SIZE` | `9` / `15` | 字号范围 |
| `ROW_GAP` | `15` | 扫描行距 |
| `WORD_GAP` | `3` | 词间距 |
| `PARTICLE_COUNT` | `28` | 漂浮小爱心数量 |
| `BUILD_INTERVAL_MS` | `220` | 外围每个文字片段出现的间隔 |
| `STROKE_INTERVAL_MS` | `50` | 中央每个笔段的间隔 |

## 实现要点

- 爱心轮廓由 4 段三次贝塞尔曲线拼成（凹口 → 右瓣 → 右外轮廓 → 底尖 → 左外轮廓 → 左瓣 → 凹口）
- 同一组曲线按 `INNER_HEART_SCALE` 生成内层心形，用水平扫描线求交点得到区间，再做区间相减，得到真正的“空心带”区域
- 在每个扫描行的空心带区间内按可用宽度自适应排字；窄处自动降字号，尽量不让轮廓断开
- 中央标题不用系统字形，而是按自定义单线笔画路径逐段细分绘制，所以有“手写”效果

## License

MIT
