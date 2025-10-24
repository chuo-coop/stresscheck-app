# ------------------------------------------------------------
# ストレスチェック簡易版（中大生協セルフケア） ver1.6（厚労省方式準拠・全面改訂）
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
st.set_page_config(page_title="ストレスチェック簡易版 - ver1.6", layout="centered")
plt.rcParams['font.family'] = 'IPAexGothic'
plt.rcParams['axes.unicode_minus'] = False

APP_TITLE = "ストレスチェック簡易版"
DESC = (
    "本チェックは厚生労働省の「職業性ストレス簡易調査票（57項目）」を参考に構成した、"
    "中大生協セルフケア版です。回答結果は端末内のみで処理され、保存・送信は行われません。"
)

# カラー設定
COLORS = {"A": "#8B0000", "B": "#003366", "C": "#004B23", "D": "#7B3F00", "AVG": "#666666"}

# ========== 回答選択肢 ==========
CHOICES_AGREE = [
    "1：そうではない", "2：あまりそうではない", "3：どちらともいえない",
    "4：ややそうだ", "5：そうだ"
]
CHOICES_FREQ = [
    "1：ほとんどない", "2：あまりない", "3：どちらともいえない",
    "4：ときどきある", "5：よくある"
]

# ========== 設問 ==========
QUESTIONS = [
    # A群（17：仕事のストレス要因） ← この群は「高いほど負担が強い」に正規化する
    "自分のペースで仕事ができる。","仕事の量が多い。","時間内に仕事を終えるのが難しい。",
    "仕事の内容が高度である。","自分の知識や技能を使う仕事である。","仕事に対して裁量がある。",
    "自分の仕事の役割がはっきりしている。","自分の仕事が組織の中で重要だと思う。",
    "仕事の成果が報われると感じる。","職場の雰囲気が良い。","職場の人間関係で気を使う。",
    "上司からのサポートが得られる。","同僚からのサポートが得られる。","仕事上の相談ができる相手がいる。",
    "顧客や取引先との関係がうまくいっている。","自分の意見が職場で尊重されている。","職場に自分の居場所がある。",
    # B群（29：ストレス反応） ← そのまま加点。「高いほど反応が強い」
    "活気がある。","仕事に集中できる。","気分が晴れない。","ゆううつだ。","怒りっぽい。","イライラする。",
    "落ち着かない。","不安だ。","眠れない。","疲れやすい。","体がだるい。","頭が重い。","肩こりや腰痛がある。",
    "胃が痛い、食欲がない。","動悸や息苦しさがある。","手足の冷え、しびれがある。","めまいやふらつきがある。",
    "体調がすぐれないと感じる。","仕事をする気力が出ない。","集中力が続かない。","物事を楽しめない。",
    "自分を責めることが多い。","周りの人に対して興味がわかない。","自分には価値がないと感じる。",
    "将来に希望がもてない。","眠っても疲れがとれない。","小さなことが気になる。","涙もろくなる。","休日も疲れが残る。",
    # C群（9：周囲のサポート） ← そのまま加点。「高いほど支援が多い」
    "上司はあなたの意見を聞いてくれる。","上司は相談にのってくれる。","上司は公平に扱ってくれる。",
    "同僚は困ったとき助けてくれる。","同僚とは気軽に話ができる。","同僚と協力しながら仕事ができる。",
    "家族や友人はあなたを支えてくれる。","家族や友人に悩みを話せる。","家族や友人はあなたの仕事を理解してくれる。",
    # D群（2：満足度） ← そのまま加点。「高いほど満足度が高い」
    "現在の仕事に満足している。","現在の生活に満足している。"
]

# 群別タイプ（参考：使わないが構造把握用）
Q_TYPE = [
    "A","A","A","A","A","A","A","A","A","A","A","A","A","A","A","A","A",
    "B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B",
    "C","C","C","C","C","C","C","C","C",
    "D","D"
]

# ========== 状態管理 ==========
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

# ========== UI ==========
st.image("TITLE.png", use_column_width=True)
st.markdown(
    "<p style='text-align:center; font-size:16px;'>"
    + DESC +
    "</p>",
    unsafe_allow_html=True
)
st.markdown("<hr>", unsafe_allow_html=True)

if st.session_state.page < len(QUESTIONS):
    q_num = st.session_state.page + 1
    st.subheader(f"Q{q_num} / {len(QUESTIONS)}")
    st.write(QUESTIONS[st.session_state.page])

    # A/B/C/D 群で選択肢を自動切替（Bのみ頻度尺度）
    if st.session_state.page < 17:
        choice_set = CHOICES_AGREE
    elif st.session_state.page < 46:
        choice_set = CHOICES_FREQ
    else:
        choice_set = CHOICES_AGREE

    prev_val = st.session_state.answers[st.session_state.page]
    index_val = (prev_val - 1) if prev_val else None

    choice = st.radio("回答を選んでください：", choice_set, index=index_val, key=f"q_{q_num}")

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # --- ボタン配置：縦方向（次へ→前へ） ---
    if choice:
        st.session_state.answers[st.session_state.page] = choice_set.index(choice) + 1
        if st.button("次へ ▶", use_container_width=False):
            go_next()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if st.session_state.page > 0:
        if st.button("◀ 前へ", use_container_width=False):
            go_prev()

else:
    # ===== 解析 =====
    st.success("🎉 回答完了！解析を開始します。")

    ans = st.session_state.answers
    A_raw, B_raw, C_raw, D_raw = ans[0:17], ans[17:46], ans[46:55], ans[55:57]

    # --- 厚労省方式に即した向き統一 ---
    # A群：ポジティブ項目を反転して「高いほど負担が強い」に統一
    # 0-based index（Aの中でネガは [1,2,10] とし、その他は反転）
    A_pos_rev_idx = [0,3,4,5,6,7,8,9,11,12,13,14,15,16]  # ポジティブ項目
    A_proc = [(6 - v if i in A_pos_rev_idx else v) for i, v in enumerate(A_raw)]

    # B群：そのまま（高いほど反応が強い）
    B_proc = B_raw[:]

    # C群・D群：そのまま（高いほど良い）
    C_proc = C_raw[:]
    D_proc = D_raw[:]

    # --- 0〜100 正規化 ---
    def normalize(val, n):
        return round((val - n) / (4 * n) * 100, 1)

    A_score = normalize(sum(A_proc), len(A_proc))   # 高いほど悪い
    B_score = normalize(sum(B_proc), len(B_proc))   # 高いほど悪い
    C_score = normalize(sum(C_proc), len(C_proc))   # 高いほど良い
    D_score = normalize(sum(D_proc), len(D_proc))   # 高いほど良い

    my_vals = [A_score, B_score, C_score, D_score]
    nat_vals = [45, 40, 35, 30]  # 仮想的な比較参照（運用で調整可）

    # --- 判定ロジック（実務寄り簡易版） ---
    # 高ストレス：Bが高い、かつ Aが高い or C/Dが低い
    if B_score >= 60:
        status = "高ストレス状態（専門医への相談をおすすめします）"
    elif B_score >= 50 and (A_score >= 55 or C_score <= 45 or D_score <= 45):
        status = "注意：ストレス反応や職場要因がやや高い水準です"
    else:
        status = "概ね安定しています（現状維持を心がけましょう）"

    # ===== 総合判定表示 =====
    st.subheader("総合判定")
    st.markdown(
        f"<p style='font-size:18px; font-weight:700; color:{COLORS['A']};'>{status}</p>",
        unsafe_allow_html=True
    )

    # ===== レーダーチャート =====
    labels = ["A(負担)", "B(反応)", "C(支援)", "D(満足)"]
    user = my_vals + [my_vals[0]]
    avg = nat_vals + [nat_vals[0]]
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist() + [0]

    fig, ax = plt.subplots(figsize=(4.6, 4.6), subplot_kw=dict(polar=True))
    ax.plot(angles, user, color=COLORS["A"], linewidth=2, label="あなた")
    ax.fill(angles, user, color=COLORS["A"], alpha=0.15)
    ax.plot(angles, avg, color=COLORS["AVG"], linestyle="--", linewidth=1.5, label="全国平均（参考）")
    ax.fill(angles, avg, color=COLORS["AVG"], alpha=0.05)
    ax.set_xticks(angles[:-1])
    for t, col in zip(ax.set_xticklabels(labels), [COLORS["A"], COLORS["B"], COLORS["C"], COLORS["D"]]):
        t.set_color(col); t.set_fontweight("bold")
    ax.set_yticklabels([])
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12))
    st.pyplot(fig)

    # ===== 各群スコア表示 =====
    st.subheader("解析サマリー（全国平均との比較）")
    summary_blocks = [
        ("A. 仕事の負担感", A_score, nat_vals[0], "高いほど負担が強い（悪い傾向）", COLORS["A"]),
        ("B. からだと気持ちの反応", B_score, nat_vals[1], "高いほど反応が強い（悪い傾向）", COLORS["B"]),
        ("C. 周囲のサポート", C_score, nat_vals[2], "高いほど支援が多い（良い傾向）", COLORS["C"]),
        ("D. 仕事や生活の満足感", D_score, nat_vals[3], "高いほど満足度が高い（良い傾向）", COLORS["D"]),
    ]
    for title, val, avgv, meaning, color in summary_blocks:
        st.markdown(
            f"<div style='margin:8px 0; padding:6px 0; border-bottom:1px solid #ccc;'>"
            f"<span style='color:{color}; font-weight:700'>{title}</span><br>"
            f"<span style='color:{color}; font-size:15px;'>あなた：{val:.1f}　全国平均：{avgv:.1f}</span><br>"
            f"<span style='font-size:13px; color:#333;'>{meaning}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    # ===== PDF生成 =====
    buf, img_buf = io.BytesIO(), io.BytesIO()
    fig.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)

    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
    c = canvas.Canvas(buf, pagesize=A4)

    # --- PNGヘッダー（中央寄せ配置・透過対応＋白背景） ---
    header_img = ImageReader("TITLE.png")
    header_width = 500
    header_height = 90
    x = (A4[0] - header_width) / 2
    y = 760  # チャートと重ならない位置

    # 白背景（透過PNGの黒化防止）
    c.setFillColorRGB(1, 1, 1)
    c.rect(x - 5, y - 5, header_width + 10, header_height + 10, fill=1, stroke=0)

    # ヘッダー画像
    c.drawImage(header_img, x, y, width=header_width, height=header_height, mask='auto')

    # 日時と区切り線
    c.setFont("HeiseiMin-W3", 9)
    c.drawCentredString(A4[0] / 2, y - 18, f"結果作成日時：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.line(40, y - 28, A4[0] - 40, y - 28)

    # レーダーチャート（下げて配置）
    c.drawImage(ImageReader(img_buf), 60, 400, width=300, height=300)

    # 総合判定
    y_txt = 380
    c.setFont("HeiseiMin-W3", 11)
    c.drawString(40, y_txt, f"総合判定：{status}")
    y_txt -= 22

    # 各群スコア（意味付き）
    c.setFont("HeiseiMin-W3", 10)
    def set_rgb(hexcol):
        r = int(hexcol[1:3], 16) / 255
        g = int(hexcol[3:5], 16) / 255
        b = int(hexcol[5:7], 16) / 255
        c.setFillColorRGB(r, g, b)

    pdf_blocks = [
        ("A. 仕事の負担感", A_score, nat_vals[0], "高いほど負担が強い", COLORS["A"]),
        ("B. からだと気持ちの反応", B_score, nat_vals[1], "高いほど反応が強い", COLORS["B"]),
        ("C. 周囲のサポート", C_score, nat_vals[2], "高いほど支援が多い", COLORS["C"]),
        ("D. 仕事や生活の満足感", D_score, nat_vals[3], "高いほど満足度が高い", COLORS["D"]),
    ]
    for title, val, avgv, meaning, color in pdf_blocks:
        set_rgb(color)
        c.drawString(40, y_txt, f"{title}　あなた：{val:.1f}　全国平均：{avgv:.1f}　→ {meaning}")
        y_txt -= 16
        c.setFillColorRGB(0, 0, 0)

    # 注意書き
    y_txt -= 26
    c.setFont("HeiseiMin-W3", 9)
    c.drawString(40, y_txt, "【ご注意】")
    y_txt -= 15
    for line in [
        "本調査は厚生労働省「職業性ストレス簡易調査票（57項目）」を参考にした中央大学生活協同組合のセルフチェック版です。",
        "結果はご自身のストレス傾向を把握するための目安であり、医学的な診断や評価を目的とするものではありません。",
        "心身の不調が続く場合や結果に不安を感じる場合は、専門家へご相談ください。"
    ]:
        c.drawString(40, y_txt, line)
        y_txt -= 13

    y_txt -= 24
    c.drawString(40, y_txt, "Supervised by General Affairs Division / Information & Communication Team")
    y_txt -= 14
    c.drawString(40, y_txt, "Chuo University Co-op")

    c.showPage()
    c.save()

    st.download_button(
        "📄 PDFをダウンロード",
        buf.getvalue(),
        file_name="ストレスチェック簡易版_結果.pdf",
        mime="application/pdf",
    )

    st.markdown("""
---
※本チェックは簡易セルフケアを目的としたものであり、医学的診断ではありません。  
結果に不安がある場合や体調の変化が続く場合は、産業医・保健師・専門医にご相談ください。
""")

    if st.button("🔁 もう一度やり直す"):
        restart()
