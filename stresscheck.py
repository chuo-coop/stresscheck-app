# ==============================================================
# 中大生協 ストレスチェック（厚労省57項目準拠）ver4.5b
# 仕様：アプリ表示＝A4縦1枚PDFを完全一致
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

st.set_page_config(page_title="中大生協ストレスチェック", layout="centered")
plt.rcParams['font.family'] = 'IPAexGothic'
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

APP_CAPTION = "厚労省『職業性ストレス簡易調査票（57項目）』準拠／中央大学生活協同組合セルフケア版"
COL = {"A": "#8B0000", "B": "#003366", "C": "#004B23", "D": "#7B3F00"}

# --------------------------------------------------------------
# 設問定義
# --------------------------------------------------------------
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

QTYPE = (
    ["A"]*10 + ["C"]*2 + ["A"]*5 + ["B"]*29 + ["C"]*7 + ["D"]*2
)

QTYPE = (["A"]*17 + ["B"]*29 + ["C"]*9 + ["D"]*2)
REV = [
    1,0,0,0,1,1,1,1,1,1,0,1,1,1,1,1,1,
    1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,
    1,1
]
CHOICES = ["1：そうではない","2：あまりそうではない","3：どちらともいえない","4：ややそうだ","5：そうだ"]

assert len(Q)==57 and len(QTYPE)==57 and len(REV)==57

# --------------------------------------------------------------
# 状態管理
# --------------------------------------------------------------
if "page" not in st.session_state: st.session_state.page = 0
if "ans" not in st.session_state: st.session_state.ans = [None]*57

# --------------------------------------------------------------
# 計算関数
# --------------------------------------------------------------
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

def five_level(score):
    if score < 20: return 0
    elif score < 40: return 1
    elif score < 60: return 2
    elif score < 80: return 3
    else: return 4

def hex_to_rgb01(hexv): return tuple(int(hexv[i:i+2],16)/255 for i in (1,3,5))
def wrap_lines(s, width): return textwrap.wrap(s, width=width)

# --------------------------------------------------------------
# 質問ページ
# --------------------------------------------------------------
p = st.session_state.page
if p < 57:
    st.subheader(f"Q{p+1}/57")
    st.write(Q[p])
    ch = st.radio("回答を選んでください：", CHOICES, index=(st.session_state.ans[p]-1) if st.session_state.ans[p] else 0)
    if ch: st.session_state.ans[p] = CHOICES.index(ch)+1
    if st.button("次へ ▶"): st.session_state.page += 1; st.rerun()
    if p>0 and st.button("◀ 前へ"): st.session_state.page -= 1; st.rerun()

# --------------------------------------------------------------
# 結果ページ
# --------------------------------------------------------------
else:
    if any(a is None for a in st.session_state.ans):
        st.error("未回答があります。全57問に回答してください。")
        if st.button("入力に戻る"): st.session_state.page = 0; st.rerun()
        st.stop()

    sc = split_scores(st.session_state.ans)
    A,B,C,D = sc["A"],sc["B"],sc["C"],sc["D"]

    st.subheader("解析結果")
    st.markdown(f"**ストレス要因(A)：{A:.1f}　反応(B)：{B:.1f}　支援(C)：{C:.1f}　満足(D)：{D:.1f}**")

    # 表
    def dot_row(name, score):
        lv=five_level(score)
        cells=["○" if i==lv else "" for i in range(5)]
        return [name]+cells+[f"{score:.1f}"]
    df=pd.DataFrame(
        [dot_row("ストレスの要因(A)",A),dot_row("心身の反応(B)",B),
         dot_row("周囲のサポート(C)",C),dot_row("満足度(D)",D)],
        columns=["区分","低い","やや低い","普通","やや高い","高い","得点"]
    )
    st.dataframe(df, use_container_width=True)

    # PDFボタン
    buf=io.BytesIO()
    c=canvas.Canvas(buf,pagesize=A4)
    W,H=A4; M=57
    c.setFont("HeiseiMin-W3",12)
    c.drawString(M,H-60,"職業性ストレス簡易調査票（厚労省準拠）— 中大生協セルフケア版")
    c.line(M,H-65,W-M,H-65)
    c.setFont("HeiseiMin-W3",9)
    c.drawString(M,H-80,f"実施日：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y=H-110
    data=[["区分","低い","やや低い","普通","やや高い","高い","得点"],
          ["A 要因","","","","","","%.1f"%A],
          ["B 反応","","","","","","%.1f"%B],
          ["C 支援","","","","","","%.1f"%C],
          ["D 満足","","","","","","%.1f"%D]]
    table=Table(data,colWidths=[100,44,44,44,44,44,56])
    table.setStyle(TableStyle([("FONT",(0,0),(-1,-1),"HeiseiMin-W3",9),
                               ("GRID",(0,0),(-1,-1),0.4,colors.black)]))
    table.wrapOn(c,W,H)
    table.drawOn(c,M,y-100)
    c.setFont("HeiseiMin-W3",8)
    c.drawString(M,60,"※本票はセルフケアを目的とした参考資料であり、医学的診断・証明を示すものではありません。")
    c.drawString(M,48,"中央大学生活協同組合　情報通信チーム")
    c.save(); buf.seek(0)

    st.download_button("📄 PDFをダウンロード",buf.getvalue(),
        file_name=f"{datetime.now().strftime('%Y%m%d')}_StressCheck_ChuoU.pdf",
        mime="application/pdf")

    if st.button("🔁 もう一度やり直す"):
        st.session_state.page=0; st.session_state.ans=[None]*57; st.rerun()
