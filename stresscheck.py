# ------------------------------------------------------------
# ストレスチェック簡易版（中大生協セルフケア） ver1.7
# 厚労省57項目方式に準拠（A=負担↑悪 / B=反応↑悪 / C,D=↑良）
# レーダー軸=英字(A,B,C,D)、凡例=You / National Avg.
# 各群に全国平均比較コメントを自動付与（画面+PDF）
# ------------------------------------------------------------
import streamlit as st
import io
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.utils import ImageReader

# ========== 基本設定 ==========
st.set_page_config(page_title="ストレスチェック簡易版 - ver1.7", layout="centered")
plt.rcParams['font.family'] = 'IPAexGothic'   # 画面側のみ日本語（グラフは英字のみ）
plt.rcParams['axes.unicode_minus'] = False

DESC = (
    "本チェックは厚生労働省の「職業性ストレス簡易調査票（57項目）」を参考に構成した、"
    "中大生協セルフケア版です。回答結果は端末内のみで処理され、保存・送信は行われません。"
)

COLORS = {"A": "#8B0000", "B": "#003366", "C": "#004B23", "D": "#7B3F00", "AVG": "#666666"}

# ========== 回答選択肢 ==========
CHOICES_AGREE = ["1：そうではない","2：あまりそうではない","3：どちらともいえない","4：ややそうだ","5：そうだ"]
CHOICES_FREQ  = ["1：ほとんどない","2：あまりない","3：どちらともいえない","4：ときどきある","5：よくある"]

# ========== 設問 ==========
QUESTIONS = [
    # A群（17：負担）※ポジ項目は後で反転して「高い=悪い」に統一
    "自分のペースで仕事ができる。","仕事の量が多い。","時間内に仕事を終えるのが難しい。",
    "仕事の内容が高度である。","自分の知識や技能を使う仕事である。","仕事に対して裁量がある。",
    "自分の仕事の役割がはっきりしている。","自分の仕事が組織の中で重要だと思う。",
    "仕事の成果が報われると感じる。","職場の雰囲気が良い。","職場の人間関係で気を使う。",
    "上司からのサポートが得られる。","同僚からのサポートが得られる。","仕事上の相談ができる相手がいる。",
    "顧客や取引先との関係がうまくいっている。","自分の意見が職場で尊重されている。","職場に自分の居場所がある。",
    # B群（29：反応）
    "活気がある。","仕事に集中できる。","気分が晴れない。","ゆううつだ。","怒りっぽい。","イライラする。",
    "落ち着かない。","不安だ。","眠れない。","疲れやすい。","体がだるい。","頭が重い。","肩こりや腰痛がある。",
    "胃が痛い、食欲がない。","動悸や息苦しさがある。","手足の冷え、しびれがある。","めまいやふらつきがある。",
    "体調がすぐれないと感じる。","仕事をする気力が出ない。","集中力が続かない。","物事を楽しめない。",
    "自分を責めることが多い。","周りの人に対して興味がわかない。","自分には価値がないと感じる。",
    "将来に希望がもてない。","眠っても疲れがとれない。","小さなことが気になる。","涙もろくなる。","休日も疲れが残る。",
    # C群（9：支援）
    "上司はあなたの意見を聞いてくれる。","上司は相談にのってくれる。","上司は公平に扱ってくれる。",
    "同僚は困ったとき助けてくれる。","同僚とは気軽に話ができる。","同僚と協力しながら仕事ができる。",
    "家族や友人はあなたを支えてくれる。","家族や友人に悩みを話せる。","家族や友人はあなたの仕事を理解してくれる。",
    # D群（2：満足）
    "現在の仕事に満足している。","現在の生活に満足している。"
]

# ========== 状態 ==========
if "page" not in st.session_state:
    st.session_state.page = 0
if "answers" not in st.session_state:
    st.session_state.answers = [None] * len(QUESTIONS)

def go_next():
    st.session_state.page += 1
    st.rerun()
def go_prev():
    if st.session_state.page > 0:
        st.session_state.page -= 1
        st.rerun()
def restart():
    st.session_state.page = 0
    st.session_state.answers = [None] * len(QUESTIONS)
    st.rerun()

# ========== 画面ヘッダー ==========
st.image("TITLE.png", use_column_width=True)
st.markdown(f"<p style='text-align:center; font-size:16px;'>{DESC}</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ========== 入力UI ==========
if st.session_state.page < len(QUESTIONS):
    qn = st.session_state.page + 1
    st.subheader(f"Q{qn} / {len(QUESTIONS)}")
    st.write(QUESTIONS[st.session_state.page])

    # B群のみ頻度尺度
    choice_set = CHOICES_FREQ if (17 <= st.session_state.page < 46) else CHOICES_AGREE
    prev = st.session_state.answers[st.session_state.page]
    idx = (prev - 1) if prev else None

    choice = st.radio("回答を選んでください：", choice_set, index=idx, key=f"q_{qn}")

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    if choice:
        st.session_state.answers[st.session_state.page] = choice_set.index(choice) + 1
        if st.button("次へ ▶"):
            go_next()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    if st.session_state.page > 0:
        if st.button("◀ 前へ"):
            go_prev()

# ========== 解析 ==========
else:
    st.success("🎉 回答完了！解析を開始します。")

    ans = st.session_state.answers
    A_raw, B_raw, C_raw, D_raw = ans[0:17], ans[17:46], ans[46:55], ans[55:57]

    # --- A群：ポジ項目を反転し「高いほど負担が強い」へ統一
    # 0-based index for A: ポジ項目（良い状態）は反転
    A_pos_rev_idx = [0,3,4,5,6,7,8,9,11,12,13,14,15,16]
    A = [(6 - v if i in A_pos_rev_idx else v) for i, v in enumerate(A_raw)]
    B = B_raw[:]  # そのまま（高い=悪い）
    C = C_raw[:]  # そのまま（高い=良い）
    D = D_raw[:]  # そのまま（高い=良い）

    def normalize(val, n):
        return round((val - n) / (4 * n) * 100, 1)

    A_score, B_score = normalize(sum(A), len(A)), normalize(sum(B), len(B))
    C_score, D_score = normalize(sum(C), len(C)), normalize(sum(D), len(D))
    my_vals = [A_score, B_score, C_score, D_score]

    # 参考比較値（任意に調整可）
    nat_vals = [45, 40, 35, 30]

    # --- 総合判定 ---
    if B_score >= 60:
        status = "高ストレス状態（専門医への相談をおすすめします）"
    elif B_score >= 50 and (A_score >= 55 or C_score <= 45 or D_score <= 45):
        status = "注意：ストレス反応や職場要因がやや高い水準です"
    else:
        status = "概ね安定しています（現状維持を心がけましょう）"

    st.subheader("総合判定")
    st.markdown(f"<p style='font-size:18px; font-weight:700; color:{COLORS['A']};'>{status}</p>", unsafe_allow_html=True)

    # --- 比較コメント生成 ---
    def comment(value, avg, kind):
        # kind: 'bad_high' for A,B / 'good_high' for C,D
        diff = round(value - avg, 1)
        if kind == "bad_high":
            # プラス=悪化
            if diff >= 10:   txt = "注意が必要。対処を検討しましょう。"
            elif diff >= 5:  txt = "やや注意。負担や反応が平均より強め。"
            elif diff > -5:  txt = "平均的。様子観察で可。"
            elif diff > -10: txt = "概ね良好。適切に保てています。"
            else:            txt = "非常に良好。良い状態です。"
        else:  # good_high
            # プラス=良化
            if diff >= 10:   txt = "非常に良好。良い支援・満足度です。"
            elif diff >= 5:  txt = "概ね良好。平均より良い状態。"
            elif diff > -5:  txt = "平均的。"
            elif diff > -10: txt = "やや注意。下がり気味。"
            else:            txt = "注意。低下が目立ちます。"
        return diff, txt

    diffs_comments = {
        "A": comment(A_score, nat_vals[0], "bad_high"),
        "B": comment(B_score, nat_vals[1], "bad_high"),
        "C": comment(C_score, nat_vals[2], "good_high"),
        "D": comment(D_score, nat_vals[3], "good_high"),
    }

    # ===== レーダーチャート（英字のみ） =====
    labels = ["A", "B", "C", "D"]
    user = my_vals + [my_vals[0]]
    avg  = nat_vals + [nat_vals[0]]
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist() + [0]

    fig, ax = plt.subplots(figsize=(4.6, 4.6), subplot_kw=dict(polar=True))
    ax.plot(angles, user, color=COLORS["A"], linewidth=2, label="You")
    ax.fill(angles, user, color=COLORS["A"], alpha=0.15)
    ax.plot(angles, avg, color=COLORS["AVG"], linestyle="--", linewidth=1.5, label="National Avg.")
    ax.fill(angles, avg, color=COLORS["AVG"], alpha=0.05)
    ax.set_xticks(angles[:-1])
    for t, col in zip(ax.set_xticklabels(labels), [COLORS["A"], COLORS["B"], COLORS["C"], COLORS["D"]]):
        t.set_color(col); t.set_fontweight("bold")
    ax.set_yticklabels([])
    ax.legend(loc="upper right", bbox_to_anchor=(1.22, 1.12))
    st.pyplot(fig)

    # ===== 各群サマリー（平均比較コメント付き） =====
    st.subheader("解析サマリー（全国平均との比較）")
    blocks = [
        ("A. 仕事の負担感", "A", A_score, nat_vals[0], "高いほど負担が強い（悪い傾向）", COLORS["A"]),
        ("B. からだと気持ちの反応", "B", B_score, nat_vals[1], "高いほど反応が強い（悪い傾向）", COLORS["B"]),
        ("C. 周囲のサポート", "C", C_score, nat_vals[2], "高いほど支援が多い（良い傾向）", COLORS["C"]),
        ("D. 仕事や生活の満足感", "D", D_score, nat_vals[3], "高いほど満足度が高い（良い傾向）", COLORS["D"]),
    ]
    for title, key, val, avgv, meaning, color in blocks:
        diff, cm = diffs_comments[key]
        st.markdown(
            f"<div style='margin:8px 0; padding:6px 0; border-bottom:1px solid #ccc;'>"
            f"<span style='color:{color}; font-weight:700'>{title}</span><br>"
            f"<span style='color:{color}; font-size:15px;'>あなた：{val:.1f}　全国平均：{avgv:.1f}　（差：{diff:+.1f}）</span><br>"
            f"<span style='font-size:13px; color:#333;'>{meaning}　→ {cm}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    # ===== PDF生成 =====
    buf, img_buf = io.BytesIO(), io.BytesIO()
    fig.savefig(img_buf, format="png", bbox_inches="tight"); img_buf.seek(0)

    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
    c = canvas.Canvas(buf, pagesize=A4)

    # --- PNGヘッダー（白背景で透過対策） ---
    header_img = ImageReader("TITLE.png")
    header_width, header_height = 500, 90
    hx = (A4[0] - header_width) / 2
    hy = 760
    c.setFillColorRGB(1, 1, 1)
    c.rect(hx - 5, hy - 5, header_width + 10, header_height + 10, fill=1, stroke=0)
    c.drawImage(header_img, hx, hy, width=header_width, height=header_height, mask='auto')
    c.setFont("HeiseiMin-W3", 9)
    c.drawCentredString(A4[0]/2, hy - 18, f"結果作成日時：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.line(40, hy - 28, A4[0]-40, hy - 28)

    # レーダー画像
    c.drawImage(ImageReader(img_buf), 60, 400, width=300, height=300)

    # 総合判定
    y = 380
    c.setFont("HeiseiMin-W3", 11)
    c.drawString(40, y, f"総合判定：{status}")
    y -= 22

    # 各群（コメント付き）
    c.setFont("HeiseiMin-W3", 10)
    def set_rgb(hexcol):
        r = int(hexcol[1:3],16)/255; g = int(hexcol[3:5],16)/255; b = int(hexcol[5:7],16)/255
        c.setFillColorRGB(r,g,b)

    pdf_blocks = [
        ("A. 仕事の負担感", "A", A_score, nat_vals[0], COLORS["A"]),
        ("B. からだと気持ちの反応", "B", B_score, nat_vals[1], COLORS["B"]),
        ("C. 周囲のサポート", "C", C_score, nat_vals[2], COLORS["C"]),
        ("D. 仕事や生活の満足感", "D", D_score, nat_vals[3], COLORS["D"]),
    ]
    for title, key, val, avgv, color in pdf_blocks:
        diff, cm = diffs_comments[key]
        set_rgb(color)
        c.drawString(40, y, f"{title}　あなた：{val:.1f}　全国平均：{avgv:.1f}　（差：{diff:+.1f}）")
        y -= 14
        c.setFillColorRGB(0,0,0)
        c.drawString(60, y, f"→ {cm}")
        y -= 16

    # 注意書き
    y -= 12
    c.setFont("HeiseiMin-W3", 9)
    c.drawString(40, y, "【ご注意】")
    y -= 14
    for line in [
        "本調査は厚生労働省「職業性ストレス簡易調査票（57項目）」を参考にした中央大学生活協同組合のセルフチェック版です。",
        "結果はご自身のストレス傾向を把握するための目安であり、医学的診断を目的とするものではありません。",
        "不調が続く、数値が大きく悪化している等の場合は、医療機関・相談窓口の利用を検討してください。"
    ]:
        c.drawString(40, y, line); y -= 13

    y -= 10
    c.drawString(40, y, "Supervised by General Affairs Division / Information & Communication Team")
    y -= 14
    c.drawString(40, y, "Chuo University Co-op")
    c.showPage(); c.save()

    st.download_button(
        "📄 PDFをダウンロード",
        buf.getvalue(),
        file_name="ストレスチェック簡易版_結果.pdf",
        mime="application/pdf",
    )

    st.markdown("""
---
※本チェックは簡易セルフケアを目的としたものであり、医学的診断ではありません。  
不調が続く、または結果が気になる場合は、産業医・保健師・専門医に相談してください。
""")

    if st.button("🔁 もう一度やり直す"):
        restart()
