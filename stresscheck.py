# ==============================================================
# 中大生協 ストレスチェック（厚労省57項目準拠）ver4.5b
# 構成：総合判定 → 5段階表 → チャート3種（凡例英和対訳付）→ コメント → セルフケア → 署名
# ==============================================================

import streamlit as st
import io, numpy as np, matplotlib.pyplot as plt, pandas as pd, textwrap
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader

# ---------- 基本設定 ----------
st.set_page_config(page_title="中大生協ストレスチェック", layout="centered")

# 日本語フォント登録（フォントファイル必須）
try:
    pdfmetrics.registerFont(TTFont("IPAexGothic", "IPAexGothic.ttf"))
    addMapping('IPAexGothic', 0, 0, 'IPAexGothic')
except Exception as e:
    st.warning("日本語フォントが見つかりません。PDFの文字化けが発生する可能性があります。")
    # フォールバックなし（ReportLabはデフォルトで欧文）

# Matplotlib 日本語フォント（PDFでは使わないので英語ラベルでOK）
plt.rcParams['axes.unicode_minus'] = False

APP_CAPTION = "厚労省『職業性ストレス簡易調査票（57項目）』準拠／中央大学生活協同組合セルフケア版"
COL = {"A": "#8B0000", "B": "#003366", "C": "#004B23", "D": "#7B3F00"}

# ---------- 設問定義 ----------
Q = [
    "自分のペースで仕事ができる。","仕事の量が多い。","時間内に仕事を終えるのが難しい。","仕事の内容が高度である。",
    "自分の知識や技能を使う仕事である。","仕事に対して裁量がある。","自分の仕事の役割がはっきりしている。","自分の仕事が組織の中で重要だと思う。",
    "仕事の成果が報われると感じる。","職場の雰囲気が良い。","職場の人間関係で気を使う。","上司からのサポートが得られる。","同僚からのサポートが得られる。",
    "仕事上の相談ができる相手がいる。","顧客や取引先との関係がうまくいっている。","自分の意見が職場で尊重されている。","職場に自分の居場所がある。",
    "活気がある。","仕事に集中できる。","気分が晴れない。","ゆううつだ。","怒りっぽい。","イライラする。","落ち着かない。","不安だ。","眠れない。",
    "疲れやすい。","体がだるい。","頭が重い。","肩こりや腰痛がある。","胃が痛い、食欲がない。","動悸や息苦しさがある。","手足の冷え、しびれがある。","めまいやふらつきがある。",
    "体調がすぐれないと感じる。","仕事をする気力が出ない。","集中力が続かない。","物事を楽しめない。","自分を責めることが多い。","周りの人に対して興味がわかない。",
    "自分には価値がないと感じる。","将来に希望がもてない。","眠っても疲れがとれない。","小さなことが気になる。","涙もろくなる。","休日も疲れが残る。",
    "上司はあなたの意見を聞いてくれる。","上司は相談にのってくれる。","上司は公平に扱ってくれる。",
    "同僚は困ったとき助けてくれる。","同僚とは気軽に話ができる。","同僚と協力しながら仕事ができる。",
    "家族や友人はあなたを支えてくれる。","家族や友人に悩みを話せる。","家族や友人はあなたの仕事を理解してくれる。",
    "現在の仕事に満足している。","現在の生活に満足している。"
]
QTYPE = (["A"]*17 + ["B"]*29 + ["C"]*9 + ["D"]*2)
REV = [
    1,0,0,0,1,1,1,1,1,1,0,1,1,1,1,1,1,
    1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,
    1,1
]
CHOICES = ["1：そうではない","2：あまりそうではない","3：どちらともいえない","4：ややそうだ","5：そうだ"]
assert len(Q)==57 and len(QTYPE)==57 and len(REV)==57

# ---------- 状態 ----------
if "page" not in st.session_state: st.session_state.page = 0
if "ans" not in st.session_state: st.session_state.ans = [None]*len(Q)

# ---------- 関数 ----------
def norm100(vals): 
    if not vals: return 0
    return round((sum(vals) - len(vals)) / (4 * len(vals)) * 100, 1)

def split_scores(ans):
    g = {"A": [], "B": [], "C": [], "D": []}
    for i, x in enumerate(ans):
        if x is None: continue
        v = 6 - x if REV[i] == 1 else x
        g[QTYPE[i]].append(v)
    return {k: norm100(v) for k, v in g.items()}

def overall_label(A, B, C):
    if B >= 60 or (B >= 50 and (A >= 60 or C <= 40)): 
        return "高ストレス状態（専門家の相談を推奨）"
    if B >= 50 or A >= 55 or C <= 45: 
        return "注意：ストレス反応／職場要因がやや高い傾向"
    return "概ね安定（現状維持で可）"

def overall_comment(A, B, C):
    if B >= 60 or (B >= 50 and (A >= 60 or C <= 40)):
        return "現在の反応が強めです。まず睡眠・食事・休息の確保を優先し、業務量・締切・役割は上長と早期に調整してください。"
    if B >= 50 or A >= 55 or C <= 45:
        return "疲労や負担がやや高めです。1週間程度セルフケアを行い、改善が乏しければ職場内相談を。"
    return "大きな偏りは見られません。現在の生活リズムを維持しましょう。"

def stress_comment(a, s):
    if a == "A": return "負担高め" if s >= 60 else "概ね適正"
    if a == "B": return "疲労傾向" if s >= 50 else "安定"
    if a in ["C", "D"]: return "支援良好" if s >= 50 else "支援不足"

def five_level(s):
    return 0 if s < 20 else 1 if s < 40 else 2 if s < 60 else 3 if s < 80 else 4

def radar(values, labels, color):
    n = len(labels)
    fig, ax = plt.subplots(figsize=(3, 3), subplot_kw=dict(polar=True))
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    values = values + values[:1]
    angles = angles + angles[:1]
    ax.plot(angles, values, color=color, linewidth=2)
    ax.fill(angles, values, color=color, alpha=0.15)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color=color, fontweight="bold", fontsize=6)
    ax.set_yticklabels([])
    ax.set_ylim(0, 100)
    ax.grid(True)
    return fig

def hex_to_rgb01(h): 
    return tuple(int(h[i:i+2], 16) / 255 for i in (1, 3, 5))

def wrap_lines(s, w): 
    return textwrap.wrap(s, w)

# ---------- ページ描画 ----------
p = st.session_state.page

if p < len(Q):
    st.subheader(f"Q{p+1} / {len(Q)}")
    st.write(Q[p])
    idx = (st.session_state.ans[p] - 1) if st.session_state.ans[p] else 0
    ch = st.radio("回答を選んでください：", CHOICES, index=idx, key=f"radio_q{p}")
    if ch:
        st.session_state.ans[p] = CHOICES.index(ch) + 1
    col1, col2 = st.columns([1, 1])
    with col1:
        if p > 0 and st.button("◀ 前へ"):
            st.session_state.page -= 1
            st.rerun()
    with col2:
        if st.button("次へ ▶"):
            st.session_state.page += 1
            st.rerun()

else:
    # 結果計算
    sc = split_scores(st.session_state.ans)
    A, B, C, D = sc["A"], sc["B"], sc["C"], sc["D"]
    status_label = overall_label(A, B, C)
    status_text = overall_comment(A, B, C)

    # 結果表示
    st.subheader("解析結果")
    st.markdown(f"**総合判定：{status_label}**")
    st.markdown(status_text)

    # ---------- PDF生成 ----------
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    M = 57  # マージン
    y = H - M

    def draw_text_lines(x, y, t, size=9, w=60, l=12):
        try:
            c.setFont("IPAexGothic", size)
        except:
            c.setFont("Helvetica", size)
        for line in wrap_lines(t, w):
            c.drawString(x, y, line)
            y -= l
        return y

    # ヘッダー
    try:
        c.setFont("IPAexGothic", 12)
    except:
        c.setFont("Helvetica", 12)
    c.drawString(M, y, "職業性ストレス簡易調査票（厚労省準拠）―　中大生協セルフケア版")
    y -= 15
    try:
        c.setFont("IPAexGothic", 9)
    except:
        c.setFont("Helvetica", 9)
    c.drawString(M, y, f"実施日：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 8
    c.line(M, y, W - M, y)
    y -= 14

    # 総合判定
    try:
        c.setFont("IPAexGothic", 11)
    except:
        c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, f"【総合判定】{status_label}")
    y -= 14
    y = draw_text_lines(M + 20, y, status_text, size=9, w=60, l=12)
    y -= 6

    # 5段階表
    data = [["区分", "低い", "やや低い", "普通", "やや高い", "高い", "得点"]]
    for n, s in [("ストレスの要因（A）", A), ("心身の反応（B）", B), ("周囲のサポート（C）", C), ("満足度（D）", D)]:
        lv = five_level(s)
        data.append([n] + ["○" if i == lv else "" for i in range(5)] + [f"{s:.1f}"])
    tbl = Table(data, colWidths=[120, 44, 44, 44, 44, 44, 56])
    tbl.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "IPAexGothic", 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (1, 1), (-2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    tw, th = tbl.wrapOn(c, W, H)
    tbl.drawOn(c, M, y - th)
    y -= th + 10

    # チャート（レーダーチャート）
    chartA = radar([A] * 5, ["Workload", "Skill Use", "Job Control", "Role", "Relations"], COL["A"])
    chartB = radar([B] * 5, ["Fatigue", "Irritability", "Anxiety", "Depression", "Energy"], COL["B"])
    chartC = radar([C] * 4, ["Supervisor", "Coworker", "Family", "Satisfaction"], COL["C"])

    def fig_to_bytes(fig):
        b = io.BytesIO()
        fig.savefig(b, format="png", dpi=150, bbox_inches='tight', pad_inches=0.2)
        plt.close(fig)
        b.seek(0)
        return b

    figs = [chartA, chartB, chartC]
    titles = ["ストレスの原因と考えられる因子", "ストレスによって起こる心身の反応", "ストレス反応に影響を与える因子"]
    pairs = [
        [("Workload", "仕事の負担"), ("Skill Use", "技能の活用"), ("Job Control", "裁量"), ("Role", "役割"), ("Relations", "関係性")],
        [("Fatigue", "疲労"), ("Irritability", "いらだち"), ("Anxiety", "不安"), ("Depression", "抑うつ"), ("Energy", "活気")],
        [("Supervisor", "上司支援"), ("Coworker", "同僚支援"), ("Family", "家族・友人"), ("Satisfaction", "満足度")]
    ]
    colors_hex = [COL["A"], COL["B"], COL["C"]]
    cw, ch = 140, 140
    gap = 18
    x_positions = [M, M + cw + gap, M + (cw + gap) * 2]
    top_y = y

    # タイトルと画像
    for f, x, ttl, hc in zip(figs, x_positions, titles, colors_hex):
        r, g, b = hex_to_rgb01(hc)
        try:
            c.setFont("IPAexGothic", 7)
        except:
            c.setFont("Helvetica", 7)
        c.setFillColorRGB(r, g, b)
        c.drawCenteredString(x + cw / 2, top_y, ttl)
        c.setFillColorRGB(0, 0, 0)
        c.drawImage(ImageReader(fig_to_bytes(f)), x, top_y - ch - 6, width=cw, height=ch)

    # 凡例（英和対訳）
    yy_list = []
    for x, hc, pair in zip(x_positions, colors_hex, pairs):
        r, g, b = hex_to_rgb01(hc)
        yy = top_y - ch - 12
        try:
            c.setFont("IPAexGothic", 7)
        except:
            c.setFont("Helvetica", 7)
        for e, j in pair:
            line = f"{e}＝{j}"
            for ln in wrap_lines(line, 14):
                c.setFillColorRGB(r, g, b)
                c.drawCenteredString(x + cw / 2, yy, ln)
                yy -= 9
        c.setFillColorRGB(0, 0, 0)
        yy_list.append(yy)
    y = min(yy_list) - 8

    # コメント
    try:
        c.setFont("IPAexGothic", 11)
    except:
        c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, "【解析コメント（点数／コメント）】")
    y -= 16
    for lbl, hc, s, txt in [
        ("WORKLOAD：仕事の負担", COL["A"], A, stress_comment("A", A)),
        ("REACTION：ストレス反応", COL["B"], B, stress_comment("B", B)),
        ("SUPPORT ：周囲の支援", COL["C"], C, stress_comment("C", C)),
        ("SATISFACTION：満足度", COL["D"], D, stress_comment("D", D))
    ]:
        r, g, b = hex_to_rgb01(hc)
        c.setFillColorRGB(r, g, b)
        c.drawString(M, y, lbl)
        c.setFillColorRGB(0, 0, 0)
        y = draw_text_lines(M + 150, y, f"{s:.1f}点／{txt}", size=9, w=60, l=12)
        y -= 2
    y -= 6

    # セルフケア
    try:
        c.setFont("IPAexGothic", 11)
    except:
        c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, "【セルフケアのポイント】")
    y -= 14
    for t in ["１）睡眠・食事・軽い運動のリズムを整える。", "２）仕事の量・締切・優先順位を整理する。", "３）２週間以上続く不調は専門相談を。"]:
        try:
            c.setFont("IPAexGothic", 9)
        except:
            c.setFont("Helvetica", 9)
        c.drawString(M + 12, y, t)
        y -= 12
    y -= 4
    c.line(M, y, W - M, y)
    y -= 12
    try:
        c.setFont("IPAexGothic", 8)
    except:
        c.setFont("Helvetica", 8)
    y = draw_text_lines(M, y, "※本票はセルフケアを目的とした参考資料であり、医学的診断・証明を示すものではありません。", size=8, w=90, l=10)
    c.drawString(M, y - 10, "中央大学生活協同組合　情報通信チーム")

    c.save()
    buf.seek(0)

    # ダウンロードボタン
    st.download_button(
        label="PDFを保存",
        data=buf.getvalue(),
        file_name=f"StressCheck_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

    if st.button("もう一度やり直す"):
        st.session_state.page = 0
        st.session_state.ans = [None] * len(Q)
        st.rerun()
