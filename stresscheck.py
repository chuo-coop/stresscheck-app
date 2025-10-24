# ==============================================================
# 中大生協 ストレスチェック（厚労省57項目準拠）ver4.4b
# 仕様：アプリ表示＝A4縦1枚PDFを完全一致
# 構成順：総合判定 → 5段階表 → 3チャート（和訳付）→ 解析コメント → セルフケア → 署名
# 余白：上下 57pt（約20mm）固定
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
COL = {"A": "#8B0000", "B": "#003366", "C": "#004B23", "D": "#7B3F00"}  # A=深赤 B=濃紺 C=深緑 D=茶

# ---------- 設問定義（57） ----------
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
    1,0,0,0,1,1,1,1,1,1,0,1,1,1,1,1,1,   # A17
    1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,   # B29
    0,0,0,0,0,0,0,0,0,                                                   # C9
    1,1                                                                 # D2
]
CHOICES = ["1：そうではない","2：あまりそうではない","3：どちらともいえない","4：ややそうだ","5：そうだ"]

# 安全確認
assert len(Q)==57 and len(QTYPE)==57 and len(REV)==57

# ---------- 状態 ----------
if "page" not in st.session_state: st.session_state.page = 0
if "ans" not in st.session_state: st.session_state.ans = [None]*len(Q)

# ---------- 関数 ----------
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
        return ("現在の反応が強めです。まず睡眠・食事・休息の確保を優先し、"
                "業務量・締切・役割は上長と早期に調整してください。"
                "2週間以上つらさが続く／生活や仕事に支障が出る場合は産業医・保健師・医療機関へ相談を推奨します。")
    if B>=50 or A>=55 or C<=45:
        tips=[]
        if A>=55: tips.append("業務量・裁量・優先順位の再整理")
        if B>=50: tips.append("短時間の休息と体調リカバリー")
        if C<=45: tips.append("相談先の明確化と支援活用")
        return ("疲労や負担がやや高めです。"+ "／".join(tips) + " を1週間試行し、"
                "改善が乏しければ職場内窓口へ相談を。")
    return ("大きな偏りは見られません。現在の生活リズムを維持し、"
            "繁忙期は早めに業務量・締切・役割を共有しましょう。")

def stress_comment(area,score):
    if area=="A":
        if score>=60: return "負担感が強い傾向あり。業務量や裁量の見直しを。"
        elif score>=45: return "やや負担感の傾向あり。早めの調整を。"
        else: return "おおむね適正な範囲です。"
    elif area=="B":
        if score>=60: return "強いストレス反応。休息や専門相談を。"
        elif score>=45: return "軽い疲労・緊張の傾向があります。"
        else: return "安定しています。"
    elif area in ["C","D"]:
        if score>=60: return "支援・満足度とも良好です。"
        elif score>=45: return "一定の支援があります。"
        else: return "支援不足または満足度低下の傾向あり。早めに相談を。"

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

def hex_to_rgb01(hexv):
    return tuple(int(hexv[i:i+2],16)/255 for i in (1,3,5))

def wrap_lines(s, width): return textwrap.wrap(s, width=width)

# ---------- ヘッダ ----------
try: st.image("TITLE.png", use_column_width=True)
except Exception: st.markdown("### 中大生協ストレスチェック")
st.markdown(f"<p style='text-align:center;color:#555;'>{APP_CAPTION}</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ---------- 質問 ----------
p = st.session_state.page
if p < len(Q):
    st.subheader(f"Q{p+1} / {len(Q)}")
    st.write(Q[p])
    opts = CHOICES
    idx = (st.session_state.ans[p] - 1) if st.session_state.ans[p] else 0
    ch = st.radio("回答を選んでください：", opts, index=idx, key=f"q_{p+1}")
    if ch: st.session_state.ans[p] = CHOICES.index(ch) + 1

    # 縦配置：次へ → 前へ（宣言遵守）
    if st.button("次へ ▶"):
        st.session_state.page += 1
        st.rerun()
    if p > 0 and st.button("◀ 前へ"):
        st.session_state.page -= 1
        st.rerun()

# ---------- 解析（アプリ） ----------
else:
    # 全回答確認
    if any(a is None for a in st.session_state.ans):
        st.error("未回答があります。全57問に回答してください。")
        if st.button("入力に戻る"): st.session_state.page = 0; st.rerun()
        st.stop()

    sc = split_scores(st.session_state.ans)
    A,B,C,D = sc["A"],sc["B"],sc["C"],sc["D"]
    status_label = overall_label(A,B,C)
    status_text  = overall_comment(A,B,C)
    comments = {k: stress_comment(k, sc[k]) for k in ["A","B","C","D"]}

    # 1) 総合判定
    st.subheader("解析結果")
    st.markdown(f"**総合判定：{status_label}**")
    st.markdown(status_text)
    st.caption(f"実施日：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")

    # 2) 5段階表（画面）
    st.markdown("#### ストレス判定表（5段階）")
    st.markdown("<small>低い：20未満／やや低い：20–39／普通：40–59／やや高い：60–79／高い：80以上</small>", unsafe_allow_html=True)
    def dot_row(name, score):
        lv = five_level(score)
        cells = ["○" if i==lv else "" for i in range(5)]
        return [name] + cells + [f"{score:.1f}"]
    df = pd.DataFrame(
        [dot_row("ストレスの要因（A）", A),
         dot_row("心身の反応（B）", B),
         dot_row("周囲のサポート（C）", C),
         dot_row("満足度（D）", D)],
        columns=["区分","低い","やや低い","普通","やや高い","高い","得点"]
    )
    st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # 3) チャート（英和対訳を折返し付で下段表示）
    chartA = radar([A]*5, ["Workload","Skill Use","Job Control","Role","Relations"], COL["A"])
    chartB = radar([B]*5, ["Fatigue","Irritability","Anxiety","Depression","Energy"], COL["B"])
    chartC = radar([C]*4, ["Supervisor","Coworker","Family","Satisfaction"], COL["C"])

    charts = [
        (chartA, "ストレスの原因と考えられる因子", COL["A"],
         [("Workload","仕事の負担"),("Skill Use","技能の活用"),("Job Control","裁量"),("Role","役割"),("Relations","関係性")]),
        (chartB, "ストレスによって起こる心身の反応", COL["B"],
         [("Fatigue","疲労"),("Irritability","いらだち"),("Anxiety","不安"),("Depression","抑うつ"),("Energy","活気")]),
        (chartC, "ストレス反応に影響を与える因子", COL["C"],
         [("Supervisor","上司支援"),("Coworker","同僚支援"),("Family","家族・友人"),("Satisfaction","満足度")]),
    ]
    st.markdown("#### ストレスプロファイル図")
    c1,c2,c3 = st.columns(3)
    for (fig, title, color, pairs), col in zip(charts, [c1,c2,c3]):
        with col:
            st.markdown(f"**{title}**")
            st.pyplot(fig)
            items_html=[]
            for e,j in pairs:
                line = f"{e}＝{j}"
                wrapped = "<br>".join(wrap_lines(line, 14))
                items_html.append(f"<span style='font-size:11px;line-height:1.35'><b style='color:{color}'>{wrapped}</b></span>")
            st.markdown(f"<div style='text-align:center'>{'<br>'.join(items_html)}</div>", unsafe_allow_html=True)

    # 4) 解析コメント
    st.markdown("#### 解析コメント（点数／コメント）")
    for label,color,score,txt in [
        ("WORKLOAD：仕事の負担",COL["A"],A,comments["A"]),
        ("REACTION：ストレス反応",COL["B"],B,comments["B"]),
        ("SUPPORT ：周囲の支援",COL["C"],C,comments["C"]),
        ("SATISFACTION：満足度",COL["D"],D,comments["D"]),
    ]:
        st.markdown(f"<span style='color:{color};font-weight:bold'>{label}</span>：{score:.1f}点／{txt}", unsafe_allow_html=True)

    # 5) セルフケア
    st.markdown("#### セルフケアのポイント")
    for t in [
        "１）睡眠・食事・軽い運動のリズムを整える。",
        "２）仕事の量・締切・優先順位を整理する。",
        "３）２週間以上続く不調は専門相談を。"
    ]: st.write(t)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.caption("※本票はセルフケアを目的とした参考資料であり、医学的診断・証明を示すものではありません。")
    st.caption("中央大学生活協同組合　情報通信チーム")

    # ---------- PDF（A4縦1枚／表示と完全一致） ----------
    if st.button("💾 PDFを保存"):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        W,H = A4
        MARGIN = 57  # 20mm
        y = H - MARGIN

        def draw_text_lines(x, y, text, font="HeiseiMin-W3", size=9, width=60, leading=12):
            c.setFont(font, size)
            for line in wrap_lines(text, width):
                c.drawString(x, y, line); y -= leading
            return y

        # ヘッダ
        c.setFont("HeiseiMin-W3", 12)
        c.drawString(MARGIN, y, "職業性ストレス簡易調査票（厚労省準拠）— 中大生協セルフケア版"); y -= 15
        c.setFont("HeiseiMin-W3", 9)
        c.drawString(MARGIN, y, f"実施日：{datetime.now().strftime('%Y-%m-%d %H:%M')}"); y -= 8
        c.line(MARGIN, y, W - MARGIN, y); y -= 14

        # 1) 総合判定
        c.setFont("HeiseiMin-W3", 11)
        c.drawString(MARGIN, y, f"【総合判定】{status_label}"); y -= 14
        y = draw_text_lines(MARGIN+20, y, status_text, size=9, width=60, leading=12); y -= 6

        # 2) 5段階表
        data = [["区分","低い","やや低い","普通","やや高い","高い","得点"]]
        for name,score in [("ストレスの要因（A）",A),("心身の反応（B）",B),("周囲のサポート（C）",C),("満足度（D）",D)]:
            lv = five_level(score)
            row = [name] + ["○" if i==lv else "" for i in range(5)] + [f"{score:.1f}"]
            data.append(row)
        table = Table(data, colWidths=[120, 44,44,44,44,44, 56])
        style = TableStyle([
            ("FONT", (0,0), (-1,-1), "HeiseiMin-W3", 9),
            ("GRID", (0,0), (-1,-1), 0.4, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
            ("ALIGN", (1,1), (-2,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (0,1), (0,-1), "LEFT"),
        ])
        table.setStyle(style)
        tw, th = table.wrapOn(c, W, H)
        table.drawOn(c, MARGIN, y - th)
        y = y - th - 10
        c.setFont("HeiseiMin-W3", 8)
        y = draw_text_lines(MARGIN, y, "※列の意味：低い＝リスク小／やや低い＝経過観察／普通＝中間域／やや高い＝早期調整推奨／高い＝優先対処。", size=8, width=90, leading=10)
        y = draw_text_lines(MARGIN, y, "※各領域は100点換算。サポート・満足度は高得点ほど支援・満足が十分。", size=8, width=90, leading=10); y -= 6

        # 3) チャート3種（横並び）
        def fig_to_img_bytes(fig):
            img = io.BytesIO(); fig.savefig(img, format="png", bbox_inches="tight"); img.seek(0); return img
        figs = [chartA, chartB, chartC]
        titles_ja = ["ストレスの原因と考えられる因子","ストレスによって起こる心身の反応","ストレス反応に影響を与える因子"]
        pairs_list = [
            [("Workload","仕事の負担"),("Skill Use","技能の活用"),("Job Control","裁量"),("Role","役割"),("Relations","関係性")],
            [("Fatigue","疲労"),("Irritability","いらだち"),("Anxiety","不安"),("Depression","抑うつ"),("Energy","活気")],
            [("Supervisor","上司支援"),("Coworker","同僚支援"),("Family","家族・友人"),("Satisfaction","満足度")],
        ]
        colors_hex = [COL["A"], COL["B"], COL["C"]]
        chart_w, chart_h = 140, 140
        gap_x = 18
        x_positions = [MARGIN, MARGIN + chart_w + gap_x, MARGIN + (chart_w + gap_x)*2]
        top_y = y  # タイトル基準線
        for fig, x0, ttl, hexcol, pairs in zip(figs, x_positions, titles_ja, colors_hex, pairs_list):
            r,g,b = hex_to_rgb01(hexcol)
            c.setFont("HeiseiMin-W3", 7); c.setFillColorRGB(r,g,b)
            c.drawCentredString(x0 + chart_w/2, top_y, ttl)
            c.setFillColorRGB(0,0,0)
            img = fig_to_img_bytes(fig)
            c.drawImage(ImageReader(img), x0, top_y - chart_h - 6, width=chart_w, height=chart_h)
        # 最下段の凡例行のyを算出しながら描画
        yy_list = []
        for x0, hexcol, pairs in zip(x_positions, colors_hex, pairs_list):
            r,g,b = hex_to_rgb01(hexcol)
            yy = top_y - chart_h - 12
            c.setFont("HeiseiMin-W3", 7)
            for e,j in pairs:
                line = f"{e}＝{j}"
                for ln in wrap_lines(line, 14):
                    c.setFillColorRGB(r,g,b); c.drawCentredString(x0 + chart_w/2, yy, ln)
                    c.setFillColorRGB(0,0,0); yy -= 9
            yy_list.append(yy)
        y = min(yy_list) - 8

        # 4) 解析コメント
        c.setFont("HeiseiMin-W3", 11); c.drawString(MARGIN, y, "【解析コメント（点数／コメント）】"); y -= 16
        c.setFont("HeiseiMin-W3", 9)
        for label,hexcol,key in [("WORKLOAD：仕事の負担／",COL["A"],"A"),
                                 ("REACTION：ストレス反応／",COL["B"],"B"),
                                 ("SUPPORT ：周囲の支援／",COL["C"],"C"),
                                 ("SATISFACTION：満足度／",COL["D"],"D")]:
            r,g,b = hex_to_rgb01(hexcol)
            c.setFillColorRGB(r,g,b); c.drawString(MARGIN, y, label)
            c.setFillColorRGB(0,0,0)
            y = draw_text_lines(MARGIN+150, y, f"{sc[key]:.1f}点／{comments[key]}", size=9, width=60, leading=12)
            y -= 2

        # 5) セルフケア
        y -= 6
        c.setFont("HeiseiMin-W3", 11); c.drawString(MARGIN, y, "【セルフケアのポイント】"); y -= 14
        c.setFont("HeiseiMin-W3", 9)
        for t in ["１）睡眠・食事・軽い運動のリズムを整える。","２）仕事の量・締切・優先順位を整理する。","３）２週間以上続く不調は専門相談を。"]:
            c.drawString(MARGIN+12, y, t); y -= 12

        # 6) 署名
        y -= 4; c.line(MARGIN, y, W - MARGIN, y); y -= 12
        c.setFont("HeiseiMin-W3", 8)
        y = draw_text_lines(MARGIN, y, "※本票はセルフケアを目的とした参考資料であり、医学的診断・証明を示すものではありません。", size=8, width=90, leading=10)
        c.drawString(MARGIN, y-10, "中央大学生活協同組合　情報通信チーム")

        c.save(); buf.seek(0)
    st.download_button("💾 PDFを保存", buf.getvalue(),
        file_name=f"{datetime.now().strftime('%Y%m%d')}_StressCheck_ChuoU.pdf",
        mime="application/pdf")

    if st.button("🔁 もう一度やり直す"):
        st.session_state.page=0
        st.session_state.ans=[None]*57
        st.rerun()
