# ------------------------------------------------------------
# 中大生協 ストレスチェック（厚労省57項目準拠）ver4.0
# 1枚セルフ版 / 2枚厚労省標準版 をサイドバーで切替
# ------------------------------------------------------------
# 依存: pip install streamlit matplotlib reportlab pillow
import streamlit as st
import io, numpy as np, matplotlib.pyplot as plt
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.utils import ImageReader

# ========== 画面基本 ==========
st.set_page_config(page_title="中大生協ストレスチェック", layout="centered")
plt.rcParams['font.family'] = 'IPAexGothic'; plt.rcParams['axes.unicode_minus'] = False
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

# ========== 固定文言 ==========
APP_CAPTION = "厚生労働省『職業性ストレス簡易調査票（57項目）』準拠／中央大学生活協同組合セルフケア版"
LABELS_EN = ["Workload","Reaction","Support","Satisfaction"]
LABELS_JA = ["仕事の負担","ストレス反応","周囲の支援","満足度"]
COL = {"A":"#8B0000","B":"#003366","C":"#004B23","D":"#7B3F00"}

# ========== 設問（57）・群・逆転 ==========
Q = [
 # A17
 "自分のペースで仕事ができる。","仕事の量が多い。","時間内に仕事を終えるのが難しい。","仕事の内容が高度である。",
 "自分の知識や技能を使う仕事である。","仕事に対して裁量がある。","自分の仕事の役割がはっきりしている。","自分の仕事が組織の中で重要だと思う。",
 "仕事の成果が報われると感じる。","職場の雰囲気が良い。","職場の人間関係で気を使う。","上司からのサポートが得られる。","同僚からのサポートが得られる。",
 "仕事上の相談ができる相手がいる。","顧客や取引先との関係がうまくいっている。","自分の意見が職場で尊重されている。","職場に自分の居場所がある。",
 # B29
 "活気がある。","仕事に集中できる。","気分が晴れない。","ゆううつだ。","怒りっぽい。","イライラする。","落ち着かない。","不安だ。","眠れない。",
 "疲れやすい。","体がだるい。","頭が重い。","肩こりや腰痛がある。","胃が痛い、食欲がない。","動悸や息苦しさがある。","手足の冷え、しびれがある。","めまいやふらつきがある。",
 "体調がすぐれないと感じる。","仕事をする気力が出ない。","集中力が続かない。","物事を楽しめない。","自分を責めることが多い。","周りの人に対して興味がわかない。",
 "自分には価値がないと感じる。","将来に希望がもてない。","眠っても疲れがとれない。","小さなことが気になる。","涙もろくなる。","休日も疲れが残る。",
 # C9
 "上司はあなたの意見を聞いてくれる。","上司は相談にのってくれる。","上司は公平に扱ってくれる。",
 "同僚は困ったとき助けてくれる。","同僚とは気軽に話ができる。","同僚と協力しながら仕事ができる。",
 "家族や友人はあなたを支えてくれる。","家族や友人に悩みを話せる。","家族や友人はあなたの仕事を理解してくれる。",
 # D2
 "現在の仕事に満足している。","現在の生活に満足している。"
]
QTYPE = (["A"]*17 + ["B"]*29 + ["C"]*9 + ["D"]*2)
REV = [
 # A
 1,0,0,0, 1,1,1,1,1,1, 0,1,1,1,1,1,1,
 # B
 1,1, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
 # C
 1,1,1,1,1,1,1,1,1,
 # D
 1,1
]
CHOICES = ["1：そうではない","2：あまりそうではない","3：どちらともいえない","4：ややそうだ","5：そうだ"]

# ========== 状態 ==========
if "page" not in st.session_state: st.session_state.page = 0
if "ans" not in st.session_state: st.session_state.ans = [None]*len(Q)

# ========== 共通関数 ==========
def norm100(vals):
    s = sum(vals); n = len(vals)
    return round((s - 1*n) / (5*n - 1*n) * 100, 1)

def split_scores(ans):
    A=B=C=D=[]
    g={"A":[], "B":[], "C":[], "D":[]}
    for i,x in enumerate(ans):
        v = 6-x if REV[i]==1 else x
        g[QTYPE[i]].append(v)
    return {k:norm100(v) for k,v in g.items()}

def overall(A,B,C):
    if B>=60 or (B>=50 and (A>=60 or C<=40)): return "高ストレス状態（専門家の相談を推奨）"
    if B>=50 or A>=55 or C<=45: return "注意：ストレス反応/職場要因がやや高い傾向"
    return "概ね安定（現状維持で可）"

def comment(key, s):
    if key=="A":
        return "負担感が見られます。" if s>=60 else ("安定しています。" if s<45 else "おおむね良好。")
    if key=="B":
        return "反応が強い傾向。休息優先を。" if s>=60 else ("安定しています。" if s<45 else "軽い疲労傾向。")
    if key=="C":
        return "支援十分。" if s>=60 else ("支援不足の可能性。相談を。" if s<45 else "一定の支援あり。")
    if key=="D":
        return "満足度は高め。" if s>=60 else ("満足度が低い可能性。見直しを。" if s<45 else "概ね良好。")
    return ""

def radar(vals, color="#8B0000", size=(4.8,4.8)):
    ang = np.linspace(0, 2*np.pi, 4, endpoint=False).tolist()
    vcyc = vals + [vals[0]]; acyc = ang + [ang[0]]
    fig, ax = plt.subplots(figsize=size, subplot_kw=dict(polar=True))
    ax.plot(acyc, vcyc, color=color, linewidth=2); ax.fill(acyc, vcyc, color=color, alpha=0.15)
    ax.set_xticks(ang); ax.set_xticklabels(LABELS_EN, color=color, fontweight="bold", fontsize=11)
    ax.set_yticklabels([]); return fig

# ========== 画面ヘッダー ==========
st.image("TITLE.png", use_column_width=True)
st.markdown(f"<p style='text-align:center;color:#555;'>{APP_CAPTION}</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ========== モード切替 ==========
mode = st.sidebar.radio("PDF出力モード", ["1枚セルフ版","2枚・厚労省標準版"], index=0)

# ========== 質問 or 解析 ==========
p = st.session_state.page
if p < len(Q):
    st.subheader(f"Q{p+1} / {len(Q)}"); st.write(Q[p])
    idx = (st.session_state.ans[p]-1) if st.session_state.ans[p] else None
    ch = st.radio("回答を選んでください：", CHOICES, index=idx, key=f"q_{p+1}")
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    if ch:
        st.session_state.ans[p] = CHOICES.index(ch)+1
        if st.button("次へ ▶"): st.session_state.page += 1; st.rerun()
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if p>0 and st.button("◀ 前へ"): st.session_state.page -= 1; st.rerun()

else:
    # ===== 解析 =====
    sc = split_scores(st.session_state.ans); A,B,C,D = sc["A"],sc["B"],sc["C"],sc["D"]
    status = overall(A,B,C)
    st.subheader("解析結果"); st.caption(f"実施日：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    st.markdown(f"**総合判定：{status}**")

    # レーダー
    fig = radar([A,B,C,D]); st.pyplot(fig)

    # サマリー
    st.markdown("#### 領域別サマリー")
    for k, nm, col in [("A","仕事の負担",COL["A"]),("B","ストレス反応",COL["B"]),("C","周囲の支援",COL["C"]),("D","満足度",COL["D"])]:
        s = sc[k]
        st.markdown(f"<div style='margin:6px 0'><b style='color:{col}'>{nm}</b>：<span style='color:{col}'>{s:.1f}</span> — {comment(k,s)}</div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ===== PDF生成 =====
    buf = io.BytesIO()
    if mode=="1枚セルフ版":
        # --- 1ページ縦 ---
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont("HeiseiKakuGo-W5", 12)
        c.drawString(40, 810, "ストレスチェック簡易版（厚労省準拠／中大生協セルフケア版）")
        c.setFont("HeiseiKakuGo-W5", 9)
        c.drawString(40, 795, f"実施日：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        c.line(40,785,A4[0]-40,785)

        # レーダー画像
        img = io.BytesIO(); fig.savefig(img, format="png", bbox_inches="tight"); img.seek(0)
        w,h = 320,320; x=(A4[0]-w)/2; y=440
        c.drawImage(ImageReader(img), x, y, width=w, height=h)

        # 総合判定
        y -= 25; c.setFont("HeiseiKakuGo-W5", 11); c.drawString(40, y, f"【総合判定】{status}")
        y -= 20; c.setFont("HeiseiKakuGo-W5", 10)

        def set_rgb(hexv):
            r=int(hexv[1:3],16)/255; g=int(hexv[3:5],16)/255; b=int(hexv[5:7],16)/255
            c.setFillColorRGB(r,g,b)

        rows=[("A. Workload / 仕事の負担",A,COL["A"],comment("A",A)),
              ("B. Reaction / ストレス反応",B,COL["B"],comment("B",B)),
              ("C. Support / 周囲の支援",C,COL["C"],comment("C",C)),
              ("D. Satisfaction / 満足度",D,COL["D"],comment("D",D))]
        for t,v,colv,cm in rows:
            set_rgb(colv); c.drawString(40,y,f"{t}：{v:.1f}")
            c.setFillColorRGB(0,0,0); c.drawString(230,y,cm); y-=16

        # セルフケア助言
        y-=6; c.setFont("HeiseiKakuGo-W5",10); c.drawString(40,y,"【セルフケアのポイント】"); y-=14
        tips=["1) 睡眠・食事・軽い運動のリズムを1週間だけ整える。","2) 仕事の量/優先順位/締切を見直し、相談先を明確化。","3) 2週間以上つらい/支障が出るなら専門家へ。"]
        for t in tips: c.drawString(52,y,t); y-=14

        # 注意書き
        y-=6; c.setFont("HeiseiKakuGo-W5",9)
        c.drawString(40,y,"※本チェックはセルフケア目的であり、医学的診断ではありません。")
        y-=12; c.drawString(40,y,"※不調や不安が続く場合は医師・保健師・カウンセラーへご相談ください。")

        c.showPage(); c.save()

    else:
        # --- 2ページ横・厚労省標準型レイアウト ---
        # Page1: 判定表 + レーダー(原因/反応/影響=統合1枚)
        c = canvas.Canvas(buf, pagesize=landscape(A4))
        W,H = landscape(A4)

        # ヘッダ
        c.setFont("HeiseiKakuGo-W5", 12)
        c.drawString(40, H-40, "職業性ストレス簡易調査票（厚労省準拠）— 中大生協セルフケア版")
        c.setFont("HeiseiKakuGo-W5", 9)
        c.drawString(40, H-55, f"実施日：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        c.line(40,H-62,W-40,H-62)

        # 左エリア：簡易判定表
        y = H-90; c.setFont("HeiseiKakuGo-W5", 10)
        c.drawString(40,y,"【ストレス判定（要点）】"); y-=16
        rows=[("A. 仕事の負担",A,comment("A",A)),("B. ストレス反応",B,comment("B",B)),("C. 周囲の支援",C,comment("C",C)),("D. 満足度",D,comment("D",D))]
        for t,v,cm in rows:
            c.drawString(52,y,f"{t}：{v:.1f}"); c.drawString(180,y,cm); y-=14
        y-=8; c.setFont("HeiseiKakuGo-W5", 11); c.drawString(40,y,f"【総合判定】{status}")

        # 右エリア：レーダー
        fig2 = radar([A,B,C,D], size=(5.2,5.2))
        img2 = io.BytesIO(); fig2.savefig(img2, format="png", bbox_inches="tight"); img2.seek(0)
        c.drawImage(ImageReader(img2), W-360, H-400, width=320, height=320)

        c.showPage()

        # Page2: 注意・相談先・セルフケア助言
        c.setFont("HeiseiKakuGo-W5", 12)
        c.drawString(40, H-40, "セルフケアの手引き / 相談先の目安")
        c.setFont("HeiseiKakuGo-W5", 10)
        y = H-80
        c.drawString(40,y,"【セルフケア】"); y-=14
        tips=["1) まず睡眠時間と就寝起床時刻を一定化。","2) 仕事の負担は上長/同僚と共有し早期調整。","3) しんどさが2週間以上続く/日常に支障→医療機関へ。"]
        for t in tips: c.drawString(52,y,t); y-=14
        y-=8; c.drawString(40,y,"【相談先の目安】"); y-=14
        refs=["・産業医/保健師/カウンセラー（事業所内）","・地域のメンタルヘルス相談窓口","・かかりつけ医/心療内科/精神科"]
        for r in refs: c.drawString(52,y,r); y-=14
        y-=10; c.setFont("HeiseiKakuGo-W5", 9)
        c.drawString(40,y,"※本票はセルフケアを目的とした参考情報であり、医学的診断・証明ではありません。")
        c.showPage(); c.save()

    st.download_button("📄 PDFをダウンロード", buf.getvalue(),
        file_name=("ストレスチェック簡易版_結果.pdf" if mode=="1枚セルフ版" else "厚労省準拠_詳細版.pdf"),
        mime="application/pdf")

    if st.button("🔁 もう一度やり直す"): st.session_state.page=0; st.session_state.ans=[None]*len(Q); st.rerun()
