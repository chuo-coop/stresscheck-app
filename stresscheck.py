# ==============================================================
# 中大生協 ストレスチェック（厚労省57項目準拠）ver5.0
# ==============================================================

import streamlit as st
import io, numpy as np, matplotlib.pyplot as plt, pandas as pd, textwrap
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader

# ---------- 基本設定 ----------
st.set_page_config(page_title="中大生協ストレスチェック", layout="centered")
plt.rcParams['font.family'] = 'IPAexGothic'
plt.rcParams['axes.unicode_minus'] = False
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

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
    1,0,0,0,1,1,1,1,1,1,0,1,1,1,1,1,1, 1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,0, 1,1
]
CHOICES = ["1：そうではない","2：あまりそうではない","3：どちらともいえない","4：ややそうだ","5：そうだ"]
assert len(Q)==57 and len(QTYPE)==57 and len(REV)==57

# ---------- 状態 ----------
if "page" not in st.session_state: st.session_state.page = 0
if "ans" not in st.session_state: st.session_state.ans = [None]*len(Q)

# ---------- 関数群 ----------
def norm100(vals):
    if not vals: return 0
    s,n = sum(vals),len(vals)
    return round((s - 1*n)/(5*n - 1*n)*100,1)

def split_scores(ans):
    g={"A":[],"B":[],"C":[],"D":[]}
    for i,x in enumerate(ans):
        if x is None: continue
        v = 6-x if REV[i]==1 else x
        g[QTYPE[i]].append(v)
    return {k:norm100(v) for k,v in g.items()}

def overall_label(A,B,C):
    if B>=60 or (B>=50 and (A>=60 or C<=40)): return "高ストレス状態（専門家の相談を推奨）"
    if B>=50 or A>=55 or C<=45: return "注意：ストレス反応／職場要因がやや高い傾向"
    return "概ね安定（現状維持で可）"

def overall_comment(A,B,C):
    if B>=60 or (B>=50 and (A>=60 or C<=40)):
        return "現在の反応が強めです。まず睡眠・食事・休息を優先し、必要なら上長・医療機関へ相談を。"
    if B>=50 or A>=55 or C<=45:
        tips=[]
        if A>=55: tips.append("業務量の調整")
        if B>=50: tips.append("短時間の休息")
        if C<=45: tips.append("支援活用")
        return "疲労がやや高めです。" + "／".join(tips) + " を意識しましょう。"
    return "大きな偏りは見られません。現在の生活リズムを維持してください。"

def stress_comment(area,score):
    if area=="A":
        if score>=60: return "負担感が強い傾向あり。業務量や裁量の見直しを。"
        elif score>=45: return "やや負担感の傾向あり。早めの調整を。"
        else: return "おおむね適正です。"
    elif area=="B":
        if score>=60: return "強いストレス反応。休息や相談を。"
        elif score>=45: return "軽い疲労傾向あり。"
        else: return "安定しています。"
    elif area in ["C","D"]:
        if score>=60: return "支援・満足度とも良好です。"
        elif score>=45: return "一定の支援があります。"
        else: return "支援不足の傾向あり。相談を。"

def five_level(score):
    if score < 20: return 0
    elif score < 40: return 1
    elif score < 60: return 2
    elif score < 80: return 3
    else: return 4

def radar(vals, labels, color):
    fig, ax = plt.subplots(figsize=(3.0, 3.0), subplot_kw=dict(polar=True))
    ang = np.linspace(0,2*np.pi,len(labels),endpoint=False).tolist()
    vcyc = vals+[vals[0]]; acyc = ang+[ang[0]]
    ax.plot(acyc,vcyc,color=color,linewidth=2)
    ax.fill(acyc,vcyc,color=color,alpha=0.15)
    ax.set_xticks(ang); ax.set_xticklabels(labels,color=color,fontweight="bold",fontsize=6)
    ax.set_yticklabels([]); ax.set_ylim(0,100)
    return fig

# ---------- ヘッダ ----------
st.markdown(f"<h3 style='text-align:center'>中大生協ストレスチェック</h3>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;color:#555;'>{APP_CAPTION}</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ---------- 質問 or 解析 ----------
p = st.session_state.page
if p < len(Q):
    st.subheader(f"Q{p+1} / {len(Q)}")
    st.write(Q[p])
    opts = CHOICES
    idx = (st.session_state.ans[p] - 1) if st.session_state.ans[p] else 0
    ch = st.radio("回答を選んでください：", opts, index=idx, key=f"q_{p+1}")
    if ch: st.session_state.ans[p] = CHOICES.index(ch) + 1

    if st.button("次へ ▶"):
        st.session_state.page += 1
        st.rerun()
    if p > 0 and st.button("◀ 前へ"):
        st.session_state.page -= 1
        st.rerun()

else:
    if any(a is None for a in st.session_state.ans):
        st.error("未回答があります。全57問に回答してください。")
        if st.button("入力に戻る"): st.session_state.page = 0; st.rerun()
        st.stop()

    sc = split_scores(st.session_state.ans)
    A,B,C,D = sc["A"],sc["B"],sc["C"],sc["D"]
    status_label = overall_label(A,B,C)
    status_text  = overall_comment(A,B,C)
    comments = {k: stress_comment(k, sc[k]) for k in ["A","B","C","D"]}

    st.subheader("解析結果")
    st.markdown(f"**総合判定：{status_label}**")
    st.markdown(status_text)

    st.markdown("#### 5段階表")
    def dot_row(name, score):
        lv = five_level(score)
        cells = ["○" if i==lv else "" for i in range(5)]
        return [name] + cells + [f"{score:.1f}"]
    df = pd.DataFrame(
        [dot_row("A：ストレス要因", A),
         dot_row("B：心身反応", B),
         dot_row("C：支援", C),
         dot_row("D：満足度", D)],
        columns=["区分","低い","やや低い","普通","やや高い","高い","得点"]
    )
    st.dataframe(df, use_container_width=True)

    st.markdown("#### チャート")
    chartA = radar([A]*5, ["Workload","Skill Use","Job Control","Role","Relations"], COL["A"])
    chartB = radar([B]*5, ["Fatigue","Irritability","Anxiety","Depression","Energy"], COL["B"])
    chartC = radar([C]*4, ["Supervisor","Coworker","Family","Satisfaction"], COL["C"])
    c1,c2,c3 = st.columns(3)
    for (fig, title), col in zip([(chartA,"要因"),(chartB,"反応"),(chartC,"支援")],[c1,c2,c3]):
        with col:
            st.markdown(f"**{title}**")
            st.pyplot(fig)

    st.markdown("#### コメント")
    for label,color,key in [("A：仕事負担",COL["A"],"A"),
                            ("B：反応",COL["B"],"B"),
                            ("C：支援",COL["C"],"C"),
                            ("D：満足",COL["D"],"D")]:
        st.markdown(f"<span style='color:{color};font-weight:bold'>{label}</span>：{sc[key]:.1f}点／{comments[key]}", unsafe_allow_html=True)

    # ---------- PDF出力 ----------
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W,H = A4
    margin = 50
    y = H - margin
    c.setFont("HeiseiMin-W3", 11)
    c.drawString(margin, y, "職業性ストレス簡易調査票（厚労省準拠）— 中大生協セルフケア版")
    y -= 18
    c.setFont("HeiseiMin-W3", 9)
    c.drawString(margin, y, f"実施日：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 10
    c.line(margin, y, W - margin, y)
    y -= 20

    c.setFont("HeiseiMin-W3", 10)
    c.drawString(margin, y, f"【総合判定】{status_label}")
    y -= 14
    for line in textwrap.wrap(status_text, 70):
        c.drawString(margin + 10, y, line)
        y -= 12

    y -= 10
    data = [["区分","低い","やや低い","普通","やや高い","高い","得点"]]
    for name,score in [("A：ストレス要因",A),("B：心身反応",B),("C：支援",C),("D：満足度",D)]:
        lv = five_level(score)
        row = [name]+["○" if i==lv else "" for i in range(5)]+[f"{score:.1f}"]
        data.append(row)
    table = Table(data, colWidths=[90,40,40,40,40,40,50])
    table.setStyle(TableStyle([
        ("FONT", (0,0), (-1,-1), "HeiseiMin-W3", 8),
        ("GRID", (0,0), (-1,-1), 0.4, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("ALIGN", (1,1), (-2,-1), "CENTER")
    ]))
    tw, th = table.wrapOn(c, W, H)
    table.drawOn(c, margin, y - th)
    y -= th + 10

    def fig_to_img_bytes(fig):
        img = io.BytesIO(); fig.savefig(img, format="png", bbox_inches="tight"); img.seek(0); return img
    for fig, x in zip([chartA,chartB,chartC],[margin, margin+170, margin+340]):
        c.drawImage(ImageReader(fig_to_img_bytes(fig)), x, y - 150, width=140, height=140)
    y -= 170

    c.setFont("HeiseiMin-W3", 9)
    for label,color,key in [("A：仕事負担",COL["A"],"A"),
                            ("B：反応",COL["B"],"B"),
                            ("C：支援",COL["C"],"C"),
                            ("D：満足",COL["D"],"D")]:
        c.setFillColor(colors.HexColor(color))
        c.drawString(margin, y, f"{label}")
        c.setFillColor(colors.black)
        c.drawString(margin+60, y, f"{sc[key]:.1f}点／{comments[key]}")
        y -= 12

    y -= 8
    c.setFont("HeiseiMin-W3", 8)
    c.drawString(margin, y, "中央大学生活協同組合　情報通信チーム")
    c.save(); buf.seek(0)

    st.download_button("📄 PDFをダウンロード", buf.getvalue(),
        file_name=f"{datetime.now().strftime('%Y%m%d')}_StressCheck_ChuoU.pdf",
        mime="application/pdf")

    if st.button("🔁 もう一度やり直す"):
        st.session_state.page=0; st.session_state.ans=[None]*len(Q); st.rerun()
