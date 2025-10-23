# ------------------------------------------------------------
# ストレスチェック簡易版（中大生協セルフケア） ver1.5
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
st.set_page_config(page_title="ストレスチェック簡易版 - ver1.5", layout="centered")
plt.rcParams['font.family'] = 'IPAexGothic'
plt.rcParams['axes.unicode_minus'] = False

APP_TITLE = "ストレスチェック簡易版"
DESC = (
    "本チェックは厚生労働省の「職業性ストレス簡易調査票（57項目）」をもとに作成した、"
    "中央大学生活協同組合セルフケア版です。回答結果は端末内のみで処理され、保存・送信は行われません。"
)

# カラー（濃色固定・A=赤 / B=紺 / C=緑 / D=茶）
COLORS = {"A": "#8B0000", "B": "#003366", "C": "#004B23", "D": "#7B3F00", "AVG": "#666666"}

# ========== 回答選択肢 ==========
CHOICES_AGREE = ["1：そうではない","2：あまりそうではない","3：どちらともいえない","4：ややそうだ","5：そうだ"]
CHOICES_FREQ  = ["1：ほとんどない","2：あまりない","3：どちらともいえない","4：ときどきある","5：よくある"]

# ========== 設問 ==========
QUESTIONS = [
    # A群（17）
    "自分のペースで仕事ができる。","仕事の量が多い。","時間内に仕事を終えるのが難しい。",
    "仕事の内容が高度である。","自分の知識や技能を使う仕事である。","仕事に対して裁量がある。",
    "自分の仕事の役割がはっきりしている。","自分の仕事が組織の中で重要だと思う。",
    "仕事の成果が報われると感じる。","職場の雰囲気が良い。","職場の人間関係で気を使う。",
    "上司からのサポートが得られる。","同僚からのサポートが得られる。","仕事上の相談ができる相手がいる。",
    "顧客や取引先との関係がうまくいっている。","自分の意見が職場で尊重されている。","職場に自分の居場所がある。",
    # B群（29）
    "活気がある。","仕事に集中できる。","気分が晴れない。","ゆううつだ。","怒りっぽい。","イライラする。",
    "落ち着かない。","不安だ。","眠れない。","疲れやすい。","体がだるい。","頭が重い。","肩こりや腰痛がある。",
    "胃が痛い、食欲がない。","動悸や息苦しさがある。","手足の冷え、しびれがある。","めまいやふらつきがある。",
    "体調がすぐれないと感じる。","仕事をする気力が出ない。","集中力が続かない。","物事を楽しめない。",
    "自分を責めることが多い。","周りの人に対して興味がわかない。","自分には価値がないと感じる。",
    "将来に希望がもてない。","眠っても疲れがとれない。","小さなことが気になる。","涙もろくなる。","休日も疲れが残る。",
    # C群（9）
    "上司はあなたの意見を聞いてくれる。","上司は相談にのってくれる。","上司は公平に扱ってくれる。",
    "同僚は困ったとき助けてくれる。","同僚とは気軽に話ができる。","同僚と協力しながら仕事ができる。",
    "家族や友人はあなたを支えてくれる。","家族や友人に悩みを話せる。","家族や友人はあなたの仕事を理解してくれる。",
    # D群（2）
    "現在の仕事に満足している。","現在の生活に満足している。"
]
# 元の仕様に合わせたタイプ配列（C/Dは逆転採点）
Q_TYPE = [
"A","C","C","A","A","A","A","A","A","A","C","A","A","A","A","A","A",
"A","A","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B","B",
"A","A","A","A","A","A","A","A","A","A","A"
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
st.title(APP_TITLE)
st.write(DESC)
st.divider()

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
    c1, c2 = st.columns(2)
    with c1:  # 左：次へ
        if choice:
            st.session_state.answers[st.session_state.page] = choice_set.index(choice) + 1
            if st.button("次へ ▶"):
                go_next()
    with c2:  # 右：前へ
        if st.session_state.page > 0:
            if st.button("◀ 前へ"):
                go_prev()

else:
    # ===== 解析 =====
    st.success("🎉 回答完了！解析を開始します。")
    ans = st.session_state.answers
    A, B, C, D = ans[0:17], ans[17:46], ans[46:55], ans[55:57]
    # C/D は逆転
    C_rev, D_rev = [6 - x for x in C], [6 - x for x in D]

    def normalize(val, n):
        # (合計点 - 最低点) / (最大-最低) * 100
        return round((val - n) / (4 * n) * 100, 1)

    A_score, B_score, C_score, D_score = [normalize(sum(x), len(x)) for x in [A, B, C_rev, D_rev]]
    my_vals = [A_score, B_score, C_score, D_score]
    nat_A, nat_B, nat_C, nat_D = 45, 40, 35, 30
    nat_vals = [nat_A, nat_B, nat_C, nat_D]

    # 判定
    if B_score >= 60:
        status = "高ストレス状態（専門医への相談をおすすめします）"
    elif B_score >= 50 and (A_score >= 55 or C_score >= 55):
        status = "注意：ストレス反応や職場要因がやや高い水準です"
    else:
        status = "概ね安定しています（現状維持を心がけましょう）"

    # ===== レーダーチャート =====
    labels = ["A", "B", "C", "D"]
    user = my_vals + [my_vals[0]]
    avg  = nat_vals + [nat_vals[0]]
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist() + [0]

    fig, ax = plt.subplots(figsize=(4.2, 4.2), subplot_kw=dict(polar=True))
    # YOU / AVG
    ax.plot(angles, user, color=COLORS["A"], linewidth=2, label="YOU")
    ax.fill(angles, user, color=COLORS["A"], alpha=0.15)
    ax.plot(angles, avg, color=COLORS["AVG"], linestyle="--", linewidth=1.5, label="National AVG")
    ax.fill(angles, avg, color=COLORS["AVG"], alpha=0.05)
    # 軸ラベルをA-D色で
    ax.set_xticks(angles[:-1])
    xtick_colors = [COLORS["A"], COLORS["B"], COLORS["C"], COLORS["D"]]
    for t, col in zip(ax.set_xticklabels(labels), xtick_colors):
        t.set_color(col); t.set_fontweight("bold")
    ax.set_yticklabels([])
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12))
    st.pyplot(fig)

    # ===== スコア＋解説（統合表示） =====
    st.subheader("解析サマリー（全国平均との比較・意味つき）")
    blocks = [
        ("A. 仕事の負担感", A_score, nat_A, "高いほど負担感が強い（悪い傾向）", "業務量・裁量・役割など職場での負荷を示します。", COLORS["A"]),
        ("B. からだと気持ちの反応", B_score, nat_B, "高いほどストレス反応が強い（悪い傾向）", "疲労・感情・身体の反応を表します。", COLORS["B"]),
        ("C. 周囲のサポート", C_score, nat_C, "高いほど支援が多い（良い傾向）", "上司・同僚・家族などからの支援状況を示します。", COLORS["C"]),
        ("D. 仕事や生活の満足感", D_score, nat_D, "高いほど満足度が高い（良い傾向）", "現在の仕事・生活への満足度を表します。", COLORS["D"]),
    ]
    for title, val, avgv, meaning, desc, color in blocks:
        st.markdown(
            f"<div style='margin:6px 0'><span style='color:{color};font-weight:700'>{title}</span>　"
            f"<span style='color:{color}'>あなた：{val:.1f}　全国平均：{avgv:.1f}　→ {meaning}</span><br>"
            f"　{desc}</div>", unsafe_allow_html=True
        )

    # ===== PDF生成 =====
    buf, img_buf = io.BytesIO(), io.BytesIO()
    fig.savefig(img_buf, format="png", bbox_inches="tight"); img_buf.seek(0)

    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
    c = canvas.Canvas(buf, pagesize=A4)
    # ヘッダー（文字ベース）
    c.setFont("HeiseiMin-W3", 12)
    c.drawCentredString(A4[0]/2, 810, "ストレスチェック簡易版")
    c.setFont("HeiseiMin-W3", 9)
    c.drawCentredString(A4[0]/2, 795, f"結果作成日時：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.line(40, 785, A4[0]-40, 785)

    # チャート
    c.drawImage(ImageReader(img_buf), 60, 450, width=300, height=300)

    # 総合判定
    y = 430
    c.setFont("HeiseiMin-W3", 11)
    c.drawString(40, y, f"総合判定：{status}")
    y -= 22

    # 各ブロック（色付きタイトル＋意味→説明）
    c.setFont("HeiseiMin-W3", 10)
    def set_rgb(hexcol):
        r = int(hexcol[1:3],16)/255; g = int(hexcol[3:5],16)/255; b = int(hexcol[5:7],16)/255
        c.setFillColorRGB(r,g,b)

    for (title, val, avgv, meaning, desc, color) in blocks:
        set_rgb(color)
        c.drawString(40, y, f"{title}　あなた：{val:.1f}　全国平均：{avgv:.1f}　→ {meaning}")
        y -= 14
        c.setFillColorRGB(0,0,0)
        c.drawString(60, y, desc)
        y -= 18

    # --- 注意書き ---
    y -= 30
    c.drawString(40, y, "──────────────────────────────")
    y -= 20
    c.setFont("HeiseiMin-W3", 9)
    c.drawString(40, y, "【ご注意】")
    y -= 15

    notice = [
        "本調査は厚生労働省「職業性ストレス簡易調査票（57項目）」をもとにした",
        "中央大学生活協同組合のセルフチェック版です。",
        "結果はご自身のストレス傾向を把握するための目安であり、",
        "医学的な診断や評価を目的とするものではありません。",
        "心身の不調が続く場合や結果に不安を感じる場合は、",
        "医師・保健師・カウンセラー等の専門家へご相談ください。",
    ]
    for line in notice:
        c.drawString(40, y, line)
        y -= 14

    # --- 監修表記 ---
    y -= 30
    c.drawString(40, y, "──────────────────────────────")
    y -= 20
    c.setFont("HeiseiMin-W3", 9)
    c.drawString(40, y, "Supervised by General Affairs Division / Information & Communication Team")
    y -= 14
    c.drawString(40, y, "Chuo University Co-op")
    c.drawString(40, y - 8, "──────────────────────────────")

    # ページ終端・保存（←ここが注意！）
    c.showPage()
    c.save()

    # ===== Streamlit表示ブロックに戻る =====
    st.download_button(
        "📄 PDFをダウンロード",
        buf.getvalue(),
        file_name=f"{datetime.now().strftime('%Y%m%d')}_ストレスチェック簡易版_結果.pdf",
        mime="application/pdf",
    )

    st.markdown("""
---
※本チェックは簡易セルフケアを目的としたものであり、医学的診断ではありません。  
結果に不安がある場合や体調の変化が続く場合は、産業医・保健師・専門医にご相談ください。
""")

    if st.button("🔁 もう一度やり直す"):
        restart()
