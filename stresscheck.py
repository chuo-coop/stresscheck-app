# ------------------------------------------------------------
# ストレスチェック簡易版（厚労省準拠 × 中大生協セルフケア版）ver2.0
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
st.set_page_config(page_title="ストレスチェック簡易版 - ver2.0", layout="centered")
plt.rcParams['font.family'] = 'IPAexGothic'
plt.rcParams['axes.unicode_minus'] = False

APP_TITLE = "ストレスチェック簡易版（中大生協セルフケア版）"

# 57問（厚労省準拠・5件法）
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

# 群タイプ（A=1-17, B=18-46, C=47-55, D=56-57）
Q_TYPE = (
    ["A"]*17 +
    ["B"]*29 +
    ["C"]*9 +
    ["D"]*2
)

# 逆転項目フラグ（1=逆転, 0=通常）
# A: 1,5,6,7,8,9,10,12,13,14,15,16,17 が逆転
# B: 18,19 が逆転
# C: 47-55 全て逆転
# D: 56-57 逆転
REVERSE = [
    # A(1-17)
    1,0,0,0, 1,1,1,1,1,1, 0,1,1,1,1,1,1,
    # B(18-46)
    1,1, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    # C(47-55)
    1,1,1,1,1,1,1,1,1,
    # D(56-57)
    1,1
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
st.markdown(
    "本チェックは厚生労働省「職業性ストレス簡易調査票（57項目）」を基にしたセルフケア版です。"
    "結果は保存・送信されず、端末内のみで処理されます。"
)
st.markdown("<hr>", unsafe_allow_html=True)

if st.session_state.page < len(QUESTIONS):
    q_num = st.session_state.page + 1
    st.subheader(f"Q{q_num} / {len(QUESTIONS)}")
    st.write(QUESTIONS[st.session_state.page])
    prev_val = st.session_state.answers[st.session_state.page]
    index_val = (prev_val - 1) if prev_val else None
    choice = st.radio("回答を選んでください：", CHOICES, index=index_val, key=f"q_{q_num}")
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    if choice:
        st.session_state.answers[st.session_state.page] = CHOICES.index(choice) + 1
        if st.button("次へ ▶"):
            go_next()
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    if st.session_state.page > 0:
        if st.button("◀ 前へ"):
            go_prev()

else:
    # ===== 解析 =====
    st.success("🎉 回答完了！解析を開始します。")
    ans = st.session_state.answers
    n = len(ans)
    groups = {"A":[], "B":[], "C":[], "D":[]}
    for i in range(n):
        val = ans[i]
        if REVERSE[i]==1:
            val = 6 - val
        groups[Q_TYPE[i]].append(val)

    def normalize(vals):
        s = sum(vals)
        mn, mx = len(vals), len(vals)*5
        return round((s - mn)/(mx - mn)*100,1)

    A_score = normalize(groups["A"])
    B_score = normalize(groups["B"])
    C_score = normalize(groups["C"])
    D_score = normalize(groups["D"])
    vals = [A_score,B_score,C_score,D_score]
    labels_en = ["Workload","Reaction","Support","Satisfaction"]
    labels_ja = ["仕事の負担","ストレス反応","周囲の支援","満足度"]
    colors = ["#8B0000","#003366","#004B23","#7B3F00"]

    # ===== チャート =====
    st.subheader("ストレスプロファイル")
    angles = np.linspace(0, 2*np.pi, len(labels_en), endpoint=False).tolist()
    vals_cycle = vals + [vals[0]]
    ang_cycle = angles + [angles[0]]
    fig, ax = plt.subplots(figsize=(4.5,4.5), subplot_kw=dict(polar=True))
    ax.plot(ang_cycle, vals_cycle, color="#8B0000", linewidth=2)
    ax.fill(ang_cycle, vals_cycle, color="#8B0000", alpha=0.15)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels_en, color="#8B0000", fontweight="bold", fontsize=11)
    ax.set_yticklabels([])
    st.pyplot(fig)

    # ===== 英日対訳＋コメント =====
    st.markdown("<hr>", unsafe_allow_html=True)
    comments = []
    def eval_comment(label, score):
        if label=="Workload":
            if score>=60: return "仕事量や裁量のバランスに負担感が見られます。"
            if score<45: return "業務環境は安定しており、適切なペースで働けています。"
            return "おおむね良好ですが、無理のない働き方を意識しましょう。"
        if label=="Reaction":
            if score>=60: return "心身のストレス反応が強い傾向です。体調管理を優先してください。"
            if score<45: return "ストレス反応は安定しています。"
            return "やや疲労傾向が見られます。十分な休息を取りましょう。"
        if label=="Support":
            if score>=60: return "周囲から良い支援を得られています。"
            if score<45: return "支援が不足している可能性があります。周囲に相談を。"
            return "一定の支援が得られています。関係を大切にしましょう。"
        if label=="Satisfaction":
            if score>=60: return "満足度が高く、充実した状態です。"
            if score<45: return "満足度が低下しています。生活の見直しを。"
            return "おおむね満足できています。"
        return ""
    for l_en,l_ja,v,c in zip(labels_en,labels_ja,vals,colors):
        com = eval_comment(l_en,v)
        st.markdown(
            f"<p style='margin:6px 0;'><b><span style='color:{c}'>{l_en}</span></b>：{l_ja}／"
            f"{com}（スコア：{v:.1f}）</p>", unsafe_allow_html=True
        )

    # ===== 総合判定 =====
    if B_score>=60 or (B_score>=50 and (A_score>=60 or C_score<=40)):
        status="高ストレス状態（専門家相談推奨）"
    elif B_score>=50 or A_score>=55 or C_score<=45:
        status="注意：ストレス反応がやや高い傾向"
    else:
        status="安定：全体的に良好なバランス"
    st.markdown(f"<hr><p style='font-size:18px; font-weight:700;'>{status}</p>", unsafe_allow_html=True)

    # ===== PDF生成 =====
    buf, img_buf = io.BytesIO(), io.BytesIO()
    fig.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("HeiseiKakuGo-W5", 12)
    c.drawString(40, 800, "ストレスチェック簡易版（中大生協セルフケア版）")
    c.setFont("HeiseiKakuGo-W5", 9)
    c.drawString(40, 785, f"実施日：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.line(40,780,A4[0]-40,780)
    c.drawImage(ImageReader(img_buf), 70, 420, width=300, height=300)
    y=390
    c.setFont("HeiseiKakuGo-W5", 10)
    for l_en,l_ja,v,cx in zip(labels_en,labels_ja,vals,colors):
        c.setFillColorRGB(int(cx[1:3],16)/255,int(cx[3:5],16)/255,int(cx[5:7],16)/255)
        c.drawString(40,y,f"{l_en}：{l_ja}（{v:.1f}）")
        c.setFillColorRGB(0,0,0)
        c.drawString(150,y,eval_comment(l_en,v))
        y-=18
    y-=20
    c.setFont("HeiseiKakuGo-W5", 11)
    c.drawString(40,y,f"【総合判定】{status}")
    y-=40
    c.setFont("HeiseiKakuGo-W5", 9)
    c.drawString(40,y,"※本チェックはセルフケアを目的としたものであり、医学的診断ではありません。")
    c.showPage()
    c.save()
    st.download_button(
        "📄 PDFをダウンロード",
        buf.getvalue(),
        file_name=f"{datetime.now().strftime('%Y%m%d')}_ストレスチェック結果.pdf",
        mime="application/pdf",
    )

    if st.button("🔁 もう一度やり直す"):
        restart()
