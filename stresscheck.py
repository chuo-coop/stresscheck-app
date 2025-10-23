# ------------------------------------------------------------
# 中大生協版 職業性ストレス簡易調査 - ver1.4.1（警告除去＋自然幅ボタン）
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

# ------------------------------------------------------------
# 基本設定
# ------------------------------------------------------------
st.set_page_config(page_title="中大生協版 職業性ストレス簡易調査-ver1.4.1", layout="centered")

plt.rcParams['font.family'] = 'IPAexGothic'
plt.rcParams['axes.unicode_minus'] = False

APP_TITLE = "中大生協版 職業性ストレス簡易調査-ver1.4.1（警告除去＋自然幅ボタン）"
DESC = (
    "本チェックは厚生労働省の「職業性ストレス簡易調査票（57項目）」をもとに作成した、"
    "中央大学生活協同組合セルフケア版です。回答結果は端末内のみで処理され、保存・送信は行われません。"
)

# ------------------------------------------------------------
# カラー設定（濃色固定）
# ------------------------------------------------------------
COLOR_A = "#8B0000"   # 深赤
COLOR_B = "#003366"   # 濃紺
COLOR_C = "#004B23"   # 深緑
COLOR_D = "#7B3F00"   # 焦げ茶
COLOR_AVG = "#666666" # 全国平均（灰）

# ------------------------------------------------------------
# 回答選択肢
# ------------------------------------------------------------
CHOICES_AGREE = [
    "1：そうではない",
    "2：あまりそうではない",
    "3：どちらともいえない",
    "4：ややそうだ",
    "5：そうだ",
]

CHOICES_FREQ = [
    "1：ほとんどない",
    "2：あまりない",
    "3：どちらともいえない",
    "4：ときどきある",
    "5：よくある",
]

# ------------------------------------------------------------
# 設問リスト＋タイプ
# ------------------------------------------------------------
QUESTIONS = [
    # A群（17問）
    "自分のペースで仕事ができる。","仕事の量が多い。","時間内に仕事を終えるのが難しい。",
    "仕事の内容が高度である。","自分の知識や技能を使う仕事である。","仕事に対して裁量がある。",
    "自分の仕事の役割がはっきりしている。","自分の仕事が組織の中で重要だと思う。",
    "仕事の成果が報われると感じる。","職場の雰囲気が良い。","職場の人間関係で気を使う。",
    "上司からのサポートが得られる。","同僚からのサポートが得られる。","仕事上の相談ができる相手がいる。",
    "顧客や取引先との関係がうまくいっている。","自分の意見が職場で尊重されている。","職場に自分の居場所がある。",
    # B群（29問）
    "活気がある。","仕事に集中できる。","気分が晴れない。","ゆううつだ。","怒りっぽい。","イライラする。",
    "落ち着かない。","不安だ。","眠れない。","疲れやすい。","体がだるい。","頭が重い。","肩こりや腰痛がある。",
    "胃が痛い、食欲がない。","動悸や息苦しさがある。","手足の冷え、しびれがある。","めまいやふらつきがある。",
    "体調がすぐれないと感じる。","仕事をする気力が出ない。","集中力が続かない。","物事を楽しめない。",
    "自分を責めることが多い。","周りの人に対して興味がわかない。","自分には価値がないと感じる。",
    "将来に希望がもてない。","眠っても疲れがとれない。","小さなことが気になる。","涙もろくなる。","休日も疲れが残る。",
    # C群（9問）
    "上司はあなたの意見を聞いてくれる。","上司は相談にのってくれる。","上司は公平に扱ってくれる。",
    "同僚は困ったとき助けてくれる。","同僚とは気軽に話ができる。","同僚と協力しながら仕事ができる。",
    "家族や友人はあなたを支えてくれる。","家族や友人に悩みを話せる。","家族や友人はあなたの仕事を理解してくれる。",
    # D群（2問）
    "現在の仕事に満足している。","現在の生活に満足している。"
]
Q_TYPE = ["A"] * 17 + ["B"] * 29 + ["C"] * 9 + ["D"] * 2

# ------------------------------------------------------------
# セッション制御
# ------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = 0
if "answers" not in st.session_state:
    st.session_state.answers = [None] * len(QUESTIONS)

def next_page():
    st.session_state.page += 1
    st.rerun()

def prev_page():
    if st.session_state.page > 0:
        st.session_state.page -= 1
        st.rerun()

def restart():
    st.session_state.page = 0
    st.session_state.answers = [None] * len(QUESTIONS)
    st.rerun()

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
st.title(APP_TITLE)
st.write(DESC)
st.divider()

# ------------------------------------------------------------
# 質問ページ（左＝次へ／右＝前へ／自然幅ボタン）
# ------------------------------------------------------------
if st.session_state.page < len(QUESTIONS):
    q_num = st.session_state.page + 1
    st.subheader(f"Q{q_num} / {len(QUESTIONS)}")
    st.write(QUESTIONS[st.session_state.page])

    q_type = Q_TYPE[st.session_state.page]
    choice_set = CHOICES_FREQ if q_type == "B" else CHOICES_AGREE

    prev_val = st.session_state.answers[st.session_state.page]
    index_val = (prev_val - 1) if prev_val else None

    choice = st.radio("回答を選んでください：", choice_set, index=index_val, key=f"q_{q_num}")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])

    with col1:  # 左側：次へ
        if choice:
            st.session_state.answers[st.session_state.page] = choice_set.index(choice) + 1
            if st.button("次へ ▶"):
                next_page()

    with col2:  # 右側：前へ
        if st.session_state.page > 0:
            if st.button("◀ 前へ"):
                prev_page()

# ------------------------------------------------------------
# 集計・解析・PDF生成
# ------------------------------------------------------------
else:
    st.success("🎉 回答完了！解析を開始します。")
    answers = st.session_state.answers

    A, B, C, D = answers[0:17], answers[17:46], answers[46:55], answers[55:57]
    def normalize(val, n): 
        return round((val - n) / (4 * n) * 100, 1)

    A_score, B_score, C_score, D_score = [normalize(sum(x), len(x)) for x in [A, B, C, D]]
    nat_A, nat_B, nat_C, nat_D = 45, 40, 35, 30
    nat_vals, my_vals = [nat_A, nat_B, nat_C, nat_D], [A_score, B_score, C_score, D_score]
    diff = [round(m - n, 1) for m, n in zip(my_vals, nat_vals)]

    if B_score >= 60:
        status = "高ストレス状態（専門医への相談をおすすめします）"
    elif B_score >= 50 and (A_score >= 55 or C_score >= 55):
        status = "注意：ストレス反応や職場要因がやや高い水準です"
    else:
        status = "概ね安定しています（現状維持を心がけましょう）"

    st.subheader("解析結果（全国平均との比較）")
    st.metric("総合判定", status)
    col1, col2, col3 = st.columns(3)
    col1.metric("A：仕事の負担感", A_score, f"{diff[0]:+}")
    col2.metric("B：からだと気持ちの反応", B_score, f"{diff[1]:+}")
    col3.metric("C：周囲のサポート", C_score, f"{diff[2]:+}")
    st.metric("D：仕事や生活の満足感", D_score, f"{diff[3]:+}")

    # --------------------------------------------------------
    # レーダーチャート
    # --------------------------------------------------------
    labels = ["A", "B", "C", "D"]
    user, avg = my_vals + [my_vals[0]], nat_vals + [nat_vals[0]]
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist() + [0]

    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.plot(angles, user, color="#8B0000", linewidth=2, label="YOU")
    ax.fill(angles, user, color="#8B0000", alpha=0.15)
    ax.plot(angles, avg, color=COLOR_AVG, linestyle="--", linewidth=1.5, label="National AVG")
    ax.fill(angles, avg, color=COLOR_AVG, alpha=0.05)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color="black", fontsize=12, fontweight="bold")
    ax.set_yticklabels([])
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    st.pyplot(fig)

    # --------------------------------------------------------
    # PDF生成
    # --------------------------------------------------------
    buf, img_buf = io.BytesIO(), io.BytesIO()
    fig.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)

    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("HeiseiMin-W3", 11)
    c.drawString(40, 800, f"中大生協版 職業性ストレス簡易調査-ver1.4.1 結果（{datetime.now().strftime('%Y-%m-%d %H:%M')}）")
    c.drawImage(ImageReader(img_buf), 60, 450, width=300, height=300)

    y = 430
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(40, y, f"総合判定：{status}")
    y -= 20
    for label, score, avg in zip(["A：仕事の負担感", "B：からだと気持ちの反応", "C：周囲のサポート", "D：仕事や生活の満足感"], my_vals, nat_vals):
        c.drawString(40, y, f"{label}　あなた：{score:.1f}　全国平均：{avg:.1f}")
        y -= 16

    y -= 10
    c.setFont("HeiseiMin-W3", 9)
    c.setFillColorRGB(139/255, 0, 0);     c.drawString(40, y, "A. 仕事の負担感");  c.setFillColorRGB(0, 0, 0)
    c.drawString(140, y, "→ 業務量・裁量・役割など職場での負荷を示します。")
    y -= 14
    c.setFillColorRGB(0, 51/255, 102/255); c.drawString(40, y, "B. からだと気持ちの反応"); c.setFillColorRGB(0, 0, 0)
    c.drawString(160, y, "→ 疲労や感情面・身体面の反応を表します。")
    y -= 14
    c.setFillColorRGB(0, 75/255, 35/255); c.drawString(40, y, "C. 周囲のサポート"); c.setFillColorRGB(0, 0, 0)
    c.drawString(140, y, "→ 上司・同僚・家族などからの支援状況を示します。")
    y -= 14
    c.setFillColorRGB(123/255, 63/255, 0); c.drawString(40, y, "D. 仕事や生活の満足感"); c.setFillColorRGB(0, 0, 0)
    c.drawString(160, y, "→ 現在の仕事・生活への満足度を表します。")

    y -= 30
    c.drawString(40, y, "──────────────────────────────")
    y -= 20
    for line in [
        "本調査は厚生労働省「職業性ストレス簡易調査票（57項目）」をもとにした",
        "中央大学生活協同組合のセルフチェック版です。",
        "結果はご自身のストレス傾向を把握するための目安であり、",
        "医学的な診断や評価を目的とするものではありません。",
        "心身の不調が続く場合や結果に不安を感じる場合は、",
        "医師・保健師・カウンセラー等の専門家へご相談ください。"
    ]:
        c.drawString(40, y, line)
        y -= 14

    y -= 30
    c.drawString(40, y, "──────────────────────────────")
    y -= 20
    c.drawString(40, y, "Supervised by General Affairs Division / Information & Communication Team")
    y -= 14
    c.drawString(40, y, "Chuo University Co-op")
    c.drawString(40, y - 8, "──────────────────────────────")

    c.showPage()
    c.save()

    st.download_button(
        "📄 PDFをダウンロード",
        buf.getvalue(),
        file_name=f"{datetime.now().strftime('%Y%m%d')}_職業性ストレス簡易調査_結果.pdf",
        mime="application/pdf",
    )

    st.markdown("""
---
※本チェックは簡易セルフケアを目的としたものであり、医学的診断ではありません。  
結果に不安がある場合や体調の変化が続く場合は、産業医・保健師・専門医にご相談ください。
""")

    if st.button("🔁 もう一度やり直す"):
        restart()
