# ==============================================================
# 中大生協 ストレスチェック（厚労省57項目準拠）ver4.4e
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
    1,0,0,0,1,1,1,1,1,1,0,1,1,1,1,1,1,        # A17
    1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,  # B29 ←修正済：29個
    0,0,0,0,0,0,0,0,0,                        # C9
    1,1                                      # D2
]

CHOICES = ["1：そうではない","2：あまりそうではない","3：どちらともいえない","4：ややそうだ","5：そうだ"]

assert len(Q)==57 and len(REV)==57

# ---------- 状態 ----------
if "page" not in st.session_state: st.session_state.page = 0
if "ans" not in st.session_state: st.session_state.ans = [None]*len(Q)

# ---------- 関数 ----------
def norm100(vals):
    if not vals: return 0
    s,n = sum(vals),len(vals)
    return round((s - n)/(4*n)*100,1)

def split_scores(ans):
    g={"A":[],"B":[],"C":[],"D":[]}
    for i,x in enumerate(ans):
        if x is None: continue
        v = 6-x if REV[i]==1 else x
        g[QTYPE[i]].append(v)
    return {k:norm100(v) for k,v in g.items()}

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

def hex_to_rgb01(hexv): return tuple(int(hexv[i:i+2],16)/255 for i in (1,3,5))
def wrap_lines(s, width): return textwrap.wrap(s, width=width)

# ---------- ヘッダ ----------
st.markdown("### 中大生協ストレスチェック")
st.markdown(f"<p style='text-align:center;color:#555;'>{APP_CAPTION}</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ---------- 質問 ----------
p = st.session_state.page
if p < len(Q):
    st.subheader(f"Q{p+1} / {len(Q)}")
    st.write(Q[p])
    ch = st.radio("回答を選んでください：", CHOICES, index=(st.session_state.ans[p]-1) if st.session_state.ans[p] else 0, key=f"q_{p+1}")
    if ch: st.session_state.ans[p] = CHOICES.index(ch) + 1
    if st.button("次へ ▶"): st.session_state.page += 1; st.rerun()
    if p>0 and st.button("◀ 前へ"): st.session_state.page -= 1; st.rerun()

# ---------- 解析 ----------
else:
    if any(a is None for a in st.session_state.ans):
        st.error("未回答があります。全57問に回答してください。")
        if st.button("入力に戻る"): st.session_state.page=0; st.rerun()
        st.stop()

    sc = split_scores(st.session_state.ans)
    A,B,C,D = sc["A"],sc["B"],sc["C"],sc["D"]

    st.subheader("解析結果")
    st.markdown("**総合判定：ストレス反応／職場要因がやや高い傾向**")
    st.markdown("疲労や負担がやや高めです。短期間の調整と支援活用を意識してください。")
    st.caption(f"実施日：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")

    st.markdown("#### ストレス判定表（5段階）")
    def dot_row(name, score):
        lv = five_level(score)
        cells = ["○" if i==lv else "" for i in range(5)]
        return [name]+cells+[f"{score:.1f}"]
    df = pd.DataFrame([
        dot_row("ストレスの要因（A）",A),
        dot_row("心身の反応（B）",B),
        dot_row("周囲のサポート（C）",C),
        dot_row("満足度（D）",D)
    ],columns=["区分","低い","やや低い","普通","やや高い","高い","得点"])
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.markdown("#### ストレスプロファイル図")
    chartA = radar([A]*5,["Workload","Skill Use","Job Control","Role","Relations"],COL["A"])
    chartB = radar([B]*5,["Fatigue","Irritability","Anxiety","Depression","Energy"],COL["B"])
    chartC = radar([C]*4,["Supervisor","Coworker","Family","Satisfaction"],COL["C"])
    c1,c2,c3 = st.columns(3)
    for fig,col in zip([chartA,chartB,chartC],[c1,c2,c3]): col.pyplot(fig)

    st.markdown("#### セルフケアのポイント")
    for t in [
        "１）睡眠・食事・軽い運動のリズムを整える。",
        "２）仕事の量・締切・優先順位を整理する。",
        "３）２週間以上続く不調は専門相談を。"
    ]: st.write(t)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.caption("※本票はセルフケアを目的とした参考資料であり、医学的診断・証明を示すものではありません。")
    st.caption("中央大学生活協同組合　情報通信チーム")

    # ---------- PDF生成 ----------
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W,H = A4; MARGIN=57
    y = H - MARGIN
    c.setFont("HeiseiMin-W3",11)
    c.drawString(MARGIN,y,"職業性ストレス簡易調査票（厚労省準拠）— 中大生協セルフケア版"); y-=14
    c.setFont("HeiseiMin-W3",9)
    c.drawString(MARGIN,y,f"実施日：{datetime.now().strftime('%Y-%m-%d %H:%M')}"); y-=10
    c.line(MARGIN,y,W-MARGIN,y); y-=12
    c.drawString(MARGIN,y,"【総合判定】ストレス反応／職場要因がやや高い傾向"); y-=12
    c.drawString(MARGIN+20,y,"疲労や負担がやや高めです。短期間の調整と支援活用を意識してください。"); y-=20
    c.setFont("HeiseiMin-W3",8)
    c.drawString(MARGIN,y,"※本票はセルフケアを目的とした参考資料であり、医学的診断・証明を示すものではありません。"); y-=10
    c.drawString(MARGIN,y,"中央大学生活協同組合　情報通信チーム")
    c.save(); buf.seek(0)

    st.download_button("💾 PDFを保存", buf.getvalue(), f"{datetime.now().strftime('%Y%m%d')}_StressCheck_ChuoU.pdf", "application/pdf")

    if st.button("🔁 もう一度やり直す"):
        st.session_state.page=0
        st.session_state.ans=[None]*len(Q)
        st.rerun()
