import streamlit as st
import math
import io
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.utils import ImageReader

# ------------------------------------------------------------
# 職業性ストレス簡易調査票（57項目・設問タイプ別選択肢対応）
# ------------------------------------------------------------

APP_TITLE = "中大生協版 職業性ストレス簡易調査-ver1.0"
DESC = (
    "本チェックは厚生労働省の「職業性ストレス簡易調査票（57項目）」をもとにしたセルフケア版です。"
    "回答結果は端末内のみで処理され、保存・送信は行われません。所要時間：約7分。"
)

# ------------------------------------------------------------
# 選択肢セット（タイプ別）
# ------------------------------------------------------------
CHOICES_AGREE = [
    "1：まったくそうではない",
    "2：あまりそうではない",
    "3：どちらともいえない",
    "4：ややそうだ",
    "5：とてもそうだ",
]

CHOICES_FREQ = [
    "1：ほとんどない",
    "2：あまりない",
    "3：どちらともいえない",
    "4：ときどきある",
    "5：よくある",
]

# ------------------------------------------------------------
# 設問リスト（57問）＋タイプ指定
# ------------------------------------------------------------
QUESTIONS = [
# A群（1〜17）
"自分のペースで仕事ができる。",
"仕事の量が多い。",
"時間内に仕事を終えるのが難しい。",
"仕事の内容が高度である。",
"自分の知識や技能を使う仕事である。",
"仕事に対して裁量がある。",
"自分の仕事の役割がはっきりしている。",
"自分の仕事が組織の中で重要だと思う。",
"仕事の成果が報われると感じる。",
"職場の雰囲気が良い。",
"職場の人間関係で気を使う。",
"上司からのサポートが得られる。",
"同僚からのサポートが得られる。",
"仕事上の相談ができる相手がいる。",
"顧客や取引先との関係がうまくいっている。",
"自分の意見が職場で尊重されている。",
"職場に自分の居場所がある。",

# B群（18〜46）
"活気がある。",
"仕事に集中できる。",
"気分が晴れない。",
"ゆううつだ。",
"怒りっぽい。",
"イライラする。",
"落ち着かない。",
"不安だ。",
"眠れない。",
"疲れやすい。",
"体がだるい。",
"頭が重い。",
"肩こりや腰痛がある。",
"胃が痛い、食欲がない。",
"動悸や息苦しさがある。",
"手足の冷え、しびれがある。",
"めまいやふらつきがある。",
"体調がすぐれないと感じる。",
"仕事をする気力が出ない。",
"集中力が続かない。",
"物事を楽しめない。",
"自分を責めることが多い。",
"周りの人に対して興味がわかない。",
"自分には価値がないと感じる。",
"将来に希望がもてない。",
"眠っても疲れがとれない。",
"小さなことが気になる。",
"涙もろくなる。",
"休日も疲れが残る。",

# C群（47〜55）
"上司はあなたの意見を聞いてくれる。",
"上司は相談にのってくれる。",
"上司は公平に扱ってくれる。",
"同僚は困ったとき助けてくれる。",
"同僚とは気軽に話ができる。",
"同僚と協力しながら仕事ができる。",
"家族や友人はあなたを支えてくれる。",
"家族や友人に悩みを話せる。",
"家族や友人はあなたの仕事を理解してくれる。",

# D群（56〜57）
"現在の仕事に満足している。",
"現在の生活に満足している。"
]

# ------------------------------------------------------------
# 設問タイプ（A=同意型, B=頻度型, C=否定的文型）
# ------------------------------------------------------------
Q_TYPE = [
# A群
"A","C","C","A","A","A","A","A","A","A","C","A","A","A","A","A","A",
# B群
"A","A","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B",
# C群
"A","A","A","A","A","A","A","A","A",
# D群
"A","A"
]

# ------------------------------------------------------------
# Streamlit UI設定
# ------------------------------------------------------------
st.set_page_config(APP_TITLE, layout="centered")
st.title(APP_TITLE)
st.write(DESC)
st.divider()

if "page" not in st.session_state:
    st.session_state.page = 0
if "answers" not in st.session_state:
    st.session_state.answers = [None] * len(QUESTIONS)

def next_page():
    st.session_state.page += 1
    st.rerun()

def restart():
    st.session_state.page = 0
    st.session_state.answers = [None] * len(QUESTIONS)
    st.rerun()

# ------------------------------------------------------------
# 質問進行パート
# ------------------------------------------------------------
if st.session_state.page < len(QUESTIONS):
    q_num = st.session_state.page + 1
    st.subheader(f"Q{q_num} / {len(QUESTIONS)}")
    st.write(QUESTIONS[st.session_state.page])

    q_type = Q_TYPE[st.session_state.page]
    if q_type == "B":
        choice_set = CHOICES_FREQ
    else:
        choice_set = CHOICES_AGREE

    choice = st.radio("回答を選んでください：", choice_set, index=None, key=f"q_{q_num}")
    if choice:
        st.session_state.answers[st.session_state.page] = choice_set.index(choice) + 1
        if st.button("次へ ▶"):
            next_page()

# ------------------------------------------------------------
# 解析・結果表示
# ------------------------------------------------------------
else:
    st.success("🎉 回答完了！解析を開始します。")
    answers = st.session_state.answers

    # 群ごとに分割
    A = answers[0:17]
    B = answers[17:46]
    C = answers[46:55]
    D = answers[55:57]

    # 逆転項目（支援・満足度）
    C_rev = [6 - x for x in C]
    D_rev = [6 - x for x in D]

    def normalize(val, n):
        return round((val - n) / (n * 4) * 100, 1)

    A_score = normalize(sum(A), len(A))
    B_score = normalize(sum(B), len(B))
    C_score = normalize(sum(C_rev), len(C_rev))
    D_score = normalize(sum(D_rev), len(D_rev))
    total = round((A_score + B_score + C_score + D_score) / 4, 1)

    # 全国平均（指標値）
    nat_A, nat_B, nat_C, nat_D = 45, 40, 35, 30
    nat_vals = [nat_A, nat_B, nat_C, nat_D]
    my_vals = [A_score, B_score, C_score, D_score]
    diff = [round(m - n, 1) for m, n in zip(my_vals, nat_vals)]

    # 結果表示
    st.subheader("解析結果（全国平均との比較）")
    col1, col2, col3 = st.columns(3)
    col1.metric("職場ストレッサー指数", A_score, f"{diff[0]:+}")
    col2.metric("心身反応指数", B_score, f"{diff[1]:+}")
    col3.metric("支援不足指数", C_score, f"{diff[2]:+}")
    st.metric("満足度不足指数", D_score, f"{diff[3]:+}")
    st.metric("総合ストレス指数", total)

    # ------------------------------------------------------------
    # レーダーチャート
    # ------------------------------------------------------------
    labels = ["職場ストレッサー", "心身反応", "支援不足", "満足度不足"]
    user = my_vals + [my_vals[0]]
    avg = nat_vals + [nat_vals[0]]
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.plot(angles, user, 'r-', linewidth=2, label="あなた")
    ax.fill(angles, user, 'r', alpha=0.15)
    ax.plot(angles, avg, 'b--', linewidth=1.5, label="全国平均")
    ax.fill(angles, avg, 'b', alpha=0.05)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_yticklabels([])
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1))
    st.pyplot(fig)

    # ------------------------------------------------------------
    # PDF出力（レーダーチャート埋め込み）
    # ------------------------------------------------------------
    buf = io.BytesIO()
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)

    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(40, 800, f"職業性ストレス簡易調査 結果（{datetime.now().strftime('%Y-%m-%d %H:%M')}）")
    c.drawImage(ImageReader(img_buf), 60, 450, width=300, height=300)
    c.drawString(40, 420, f"職場ストレッサー指数：{A_score}（全国平均45）")
    c.drawString(40, 400, f"心身反応指数：{B_score}（全国平均40）")
    c.drawString(40, 380, f"支援不足指数：{C_score}（全国平均35）")
    c.drawString(40, 360, f"満足度不足指数：{D_score}（全国平均30）")
    c.drawString(40, 330, f"総合ストレス指数：{total}")
    c.drawString(40, 300, "※本結果はセルフチェックであり、医学的診断を目的とするものではありません。")
    c.showPage()
    c.save()

    st.download_button(
        "📄 PDFをダウンロード",
        buf.getvalue(),
        file_name=f"{datetime.now().strftime('%Y%m%d')}_職業性ストレス簡易調査_結果.pdf",
        mime="application/pdf",
    )

    st.divider()
    if st.button("🔁 もう一度やり直す"):
        restart()
