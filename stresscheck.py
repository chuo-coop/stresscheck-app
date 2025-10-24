# ==============================================================
# 中大生協 ストレスチェック（厚労省57項目準拠）ver4.2（完全版）
# 生協業務版：解析画面＋PDF出力統一仕様
# --------------------------------------------------------------
# 構成：
#   1ページ目：総合判定＋3レーダーチャート
#   2ページ目：解析コメント＋セルフケア助言＋注意文
# --------------------------------------------------------------
# 依存：
#   pip install streamlit matplotlib reportlab pillow numpy
# ==============================================================

import streamlit as st
import io, numpy as np, matplotlib.pyplot as plt
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.utils import ImageReader

# ========== 基本設定 ==========
st.set_page_config(page_title="中大生協ストレスチェック", layout="centered")
plt.rcParams['font.family'] = 'IPAexGothic'
plt.rcParams['axes.unicode_minus'] = False
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

APP_CAPTION = "厚労省『職業性ストレス簡易調査票（57項目）』準拠／中央大学生活協同組合セルフケア版"
COL = {"A": "#8B0000", "B": "#003366", "C": "#004B23", "D": "#7B3F00"}

# ========== 設問定義 ==========
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
    1,0,0,0,1,1,1,1,1,1,0,1,1,1,1,1,1,
    1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,
    1,1
]
CHOICES = ["1：そうではない","2：あまりそうではない","3：どちらともいえない","4：ややそうだ","5：そうだ"]

# ========== 状態管理 ==========
if "page" not in st.session_state:
    st.session_state.page = 0
if "ans" not in st.session_state:
    st.session_state.ans = [None]*len(Q)

# ========== 関数群 ==========
def norm100(vals):
    s = sum(vals)
    n = len(vals)
    return round((s - 1*n) / (5*n - 1*n) * 100, 1)

def split_scores(ans):
    g = {"A": [], "B": [], "C": [], "D": []}
    for i, x in enumerate(ans):
        if x is None:
            continue
        v = 6 - x if REV[i] == 1 else x
        g[QTYPE[i]].append(v)
    return {k: norm100(v) for k, v in g.items()}

def overall(A, B, C):
    if B >= 60 or (B >= 50 and (A >= 60 or C <= 40)):
        return "高ストレス状態（専門家の相談を推奨）"
    if B >= 50 or A >= 55 or C <= 45:
        return "注意：ストレス反応/職場要因がやや高い傾向"
    return "概ね安定（現状維持で可）"

def stress_comment(area, score):
    if area == "A":
        if score >= 60:
            return "負担感が強い傾向あり。業務量や裁量の見直しを。"
        elif score >= 45:
            return "やや負担感の傾向あり。早めの調整を。"
        else:
            return "おおむね適正な範囲です。"
    elif area == "B":
        if score >= 60:
            return "強いストレス反応が見られます。休息や専門相談を。"
        elif score >= 45:
            return "軽い疲労・緊張の傾向があります。"
        else:
            return "安定しています。"
    elif area in ["C", "D"]:
        if score >= 60:
            return "支援環境が良好で満足度も高い状態です。"
        elif score >= 45:
            return "一定の支援があります。"
        else:
            return "支援不足または満足度低下の傾向あり。周囲への相談を。"

def radar(vals, labels, color):
    ang = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    vcyc = vals + [vals[0]]
    acyc = ang + [ang[0]]
    fig, ax = plt.subplots(figsize=(4.5, 4.5), subplot_kw=dict(polar=True))
    ax.plot(acyc, vcyc, color=color, linewidth=2)
    ax.fill(acyc, vcyc, color=color, alpha=0.15)
    ax.set_xticks(ang)
    ax.set_xticklabels(labels, color=color, fontweight="bold", fontsize=9)
    ax.set_yticklabels([])
    ax.set_ylim(0, 100)
    return fig

# ========== Streamlit画面 ==========
try:
    st.image("TITLE.png", use_column_width=True)
except Exception:
    st.markdown("### 中大生協ストレスチェック")
st.markdown(f"<p style='text-align:center;color:#555;'>{APP_CAPTION}</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

p = st.session_state.page
if p < len(Q):
    st.subheader(f"Q{p+1} / {len(Q)}")
    st.write(Q[p])

    opts = CHOICES
    idx = (st.session_state.ans[p] - 1) if st.session_state.ans[p] else 0
    ch = st.radio("回答を選んでください：", opts, index=idx, key=f"q_{p+1}")

    if ch:
        st.session_state.ans[p] = CHOICES.index(ch) + 1

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("次へ ▶"):
        st.session_state.page += 1
        st.rerun()

    if p > 0:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        if st.button("◀ 前へ"):
            st.session_state.page -= 1
            st.rerun()

else:
    sc = split_scores(st.session_state.ans)
    A, B, C, D = sc["A"], sc["B"], sc["C"], sc["D"]
    status = overall(A, B, C)

    st.subheader("解析結果")
    st.markdown(f"**総合判定：{status}**")
    st.caption(f"実施日：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")

    comments = {
        "A": stress_comment("A", A),
        "B": stress_comment("B", B),
        "C": stress_comment("C", C),
        "D": stress_comment("D", D)
    }

    # --- チャート3種 ---
    chartA = radar([A]*5, ["Workload","Skill Use","Job Control","Role","Relations"], COL["A"])
    chartB = radar([B]*5, ["Fatigue","Irritability","Anxiety","Depression","Energy"], COL["B"])
    chartC = radar([C]*4, ["Supervisor","Coworker","Family","Satisfaction"], COL["C"])

    st.markdown("#### ストレスプロファイル図（業務版）")
    cols = st.columns(3)
    for fig, col in zip([chartA, chartB, chartC], cols):
        col.pyplot(fig)

    st.markdown("#### 解析コメント")
    for label, color, txt in [
        ("WORKLOAD：仕事の負担／", COL["A"], comments["A"]),
        ("REACTION：ストレス反応／", COL["B"], comments["B"]),
        ("SUPPORT ：周囲の支援／", COL["C"], comments["C"]),
        ("SATISFACTION：満足度／", COL["D"], comments["D"]),
    ]:
        st.markdown(f"<span style='color:{color};font-weight:bold'>{label}</span>{txt}", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ========== PDF生成 ==========
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    W, H = landscape(A4)

    # --- 1ページ目 ---
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(40, H-40, "職業性ストレス簡易調査票（厚労省準拠）— 中大生協セルフケア版")
    c.setFont("HeiseiMin-W3", 9)
    c.drawString(40, H-55, f"実施日：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.line(40, H-62, W-40, H-62)
    c.setFont("HeiseiMin-W3", 11)
    c.drawString(40, H-85, f"【総合判定】{status}")

    figs = [chartA, chartB, chartC]
    x0 = [60, 300, 540]
    title_en = ["Factors Considered as Causes of Stress",
                "Psychological and Physical Reactions Caused by Stress",
                "Factors Influencing Stress Reactions"]
    title_ja = ["ストレスの原因と考えられる因子",
                "ストレスによって起こる心身の反応",
                "ストレス反応に影響を与える因子"]

    for i, (f, en, jp, col) in enumerate(zip(figs, title_en, title_ja, [COL["A"], COL["B"], COL["C"]])):
        img = io.BytesIO()
        f.savefig(img, format="png", bbox_inches="tight")
        img.seek(0)
        c.drawImage(ImageReader(img), x0[i], H-440, width=210, height=210)
        c.setFont("HeiseiMin-W3", 9)
        c.drawCentredString(x0[i]+105, H-460, en)
        c.setFont("HeiseiMin-W3", 9)
        c.drawCentredString(x0[i]+105, H-475, jp)

    c.showPage()

    # --- 2ページ目 ---
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(40, H-40, "【解析コメント】")
    y = H-70
    c.setFont("HeiseiMin-W3", 10)
    comments_color = [
        ("WORKLOAD：仕事の負担／", comments["A"], COL["A"]),
        ("REACTION：ストレス反応／", comments["B"], COL["B"]),
        ("SUPPORT ：周囲の支援／", comments["C"], COL["C"]),
        ("SATISFACTION：満足度／", comments["D"], COL["D"])
    ]
    for label, text, color in comments_color:
        r, g, b = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
        c.setFillColorRGB(r, g, b)
        c.drawString(40, y, label)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(180, y, text)
        y -= 18

    y -= 10
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(40, y, "【セルフケアのポイント】")
    y -= 20
    c.setFont("HeiseiMin-W3", 10)
    tips = [
        "１）睡眠・食事・軽い運動のリズムを整える。",
        "２）仕事の量・締切・優先順位を整理する。",
        "３）２週間以上続く不調は専門相談を。"
    ]
    for t in tips:
        c.drawString(52, y, t)
        y -= 16

    y -= 10
    c.line(40, y, W-40, y)
    y -= 18
    c.setFont("HeiseiMin-W3", 9)
    note = [
        "※本票はセルフケアを目的とした参考資料であり、",
        "　医学的診断・証明を示すものではありません。",
        "　中央大学生活協同組合　情報通信チーム"
    ]
    for n in note:
        c.drawString(40, y, n)
        y -= 14

    c.showPage()
    c.save()
    buf.seek(0)

    st.download_button(
        "📄 PDFをダウンロード",
        buf.getvalue(),
        file_name=f"{datetime.now().strftime('%Y%m%d')}_ストレスチェック業務版.pdf",
        mime="application/pdf"
    )
