import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="ระบบข้อมูลเกษตรจาก API (เชียงใหม่)", layout="wide")
st.title("ระบบข้อมูลเกษตรจาก API (Live Agri-Data - เชียงใหม่)")
st.caption("ดึงข้อมูลจริงแบบสดจากอินเทอร์เน็ต และข้อมูลสภาพอากาศ/ราคาสินค้าเกษตร จ.เชียงใหม่")

HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0 Safari/537.36"),
           "Accept": "application/json"}

# ---------- ฟังก์ชันดึงอากาศสด ----------
@st.cache_data(ttl=1800)
def ดึงอากาศ(lat, lon, days):
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
           f"relative_humidity_2m_mean,wind_speed_10m_max,shortwave_radiation_sum"
           f"&timezone=Asia/Bangkok&forecast_days={days}")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    w = pd.DataFrame(resp.json()["daily"])
    w.columns = ["วันที่", "สูงสุด", "ต่ำสุด", "ฝน", "ความชื้น", "ลม", "แสง"]
    return w

# ---------- ฟังก์ชันดึงอากาศย้อนหลังเดือนมีนาคม (เชียงใหม่) ----------
@st.cache_data(ttl=86400)
def ดึงอากาศเชียงใหม่เดือนมีนาคม(year):
    lat, lon = 18.79, 98.98  # พิกัด จ.เชียงใหม่
    start_date = f"{year}-03-01"
    end_date = f"{year}-03-31"
    url = (f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
           f"&start_date={start_date}&end_date={end_date}"
           f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean,wind_speed_10m_max"
           f"&timezone=Asia/Bangkok")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    w = pd.DataFrame(resp.json()["daily"])
    w.columns = ["วันที่", "สูงสุด", "ต่ำสุด", "ฝน", "ความชื้น", "ลม"]
    return w

# ---------- ฟังก์ชันดึงระดับน้ำ ----------
@st.cache_data(ttl=1800)
def ดึงระดับน้ำ(lat, lon):
    url = (f"https://flood-api.open-meteo.com/v1/flood?latitude={lat}&longitude={lon}"
           f"&daily=river_discharge&forecast_days=30")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    r = pd.DataFrame(resp.json()["daily"])
    r.columns = ["วันที่", "ปริมาณน้ำ"]
    return r

# ราคาสำรองสินค้าเกษตร จ.เชียงใหม่
ราคาสำรอง = pd.DataFrame({
    "สินค้า": ["ลำไยอบแห้งเกรด AA", "ส้มสายน้ำผึ้งคละ", "สตรอว์เบอร์รีพระราชทาน 80",
              "ลิ้นจี่ฮงฮวย", "กะหล่ำปลี", "หอมหัวใหญ่"],
    "ราคา": [85.0, 45.0, 150.0, 65.0, 12.0, 22.5],
})

@st.cache_data(ttl=86400)
def _ดึงราคาดิบ():
    URL = "https://data.go.th/api/3/action/datastore_search"
    RESOURCE_ID = "38b840af-f119-4bea-9208-66188da5cc1b"
    resp = requests.get(URL, params={"resource_id": RESOURCE_ID, "limit": 5000},
                        headers=HEADERS, timeout=30)
    resp.raise_for_status()
    recs = resp.json()["result"]["records"]
    ราคา = pd.DataFrame(recs)
    
    # แปลงชื่อคอลัมน์สินค้าแบบยืดหยุ่น (รวม เชียงใหม่ / บึงกาฬ / สินค้า)
    for col in ["เกษตรสำคัญเชียงใหม่", "เกษตรสำคัญบึงกาฬ", "สินค้าเกษตร", "รายการสินค้า", "เกษตรสำคัญ"]:
        if col in ราคา.columns:
            ราคา = ราคา.rename(columns={col: "สินค้า"})
            break
    if "ค่า" in ราคา.columns:
        ราคา = ราคา.rename(columns={"ค่า": "ราคา"})
        
    ราคา["ราคา"] = pd.to_numeric(ราคา["ราคา"], errors="coerce")
    return ราคา

def ดึงราคาเกษตร():
    try:
        return _ดึงราคาดิบ(), True
    except Exception:
        return None, False

# สร้าง 4 แท็บ
แท็บอากาศ, แท็บอากาศมีนา, แท็บน้ำ, แท็บราคา = st.tabs(
    ["สภาพอากาศ (สด)", "สภาพอากาศเชียงใหม่ (เดือน มี.ค.)", "ระดับน้ำแม่น้ำ", "ราคาสินค้าเกษตร (เชียงใหม่)"])

# ---------- แท็บ 1: สภาพอากาศพยากรณ์สด ----------
with แท็บอากาศ:
    st.subheader("พยากรณ์อากาศรายวันของสวน (เชียงใหม่ / ทั่วไป)")
    c1, c2, c3 = st.columns(3)
    lat = c1.number_input("ละติจูด", value=18.79)
    lon = c2.number_input("ลองจิจูด", value=98.98)
    วัน = c3.slider("จำนวนวันล่วงหน้า", 3, 16, 15)
    try:
        w = ดึงอากาศ(lat, lon, วัน)
        m1, m2, m3 = st.columns(3)
        m1.metric("อุณหภูมิสูงสุดพรุ่งนี้", f"{w['สูงสุด'].iloc[1]:.0f} °C")
        m2.metric("ฝนรวม (ช่วงที่ดู)", f"{w['ฝน'].sum():.0f} มม.")
        m3.metric("ความชื้นเฉลี่ย", f"{w['ความชื้น'].mean():.0f} %")
        st.write("อุณหภูมิสูงสุด/ต่ำสุด (°C)")
        st.line_chart(w.set_index("วันที่")[["สูงสุด", "ต่ำสุด"]])
        st.write("ปริมาณฝนรายวัน (มม.)")
        st.bar_chart(w.set_index("วันที่")["ฝน"])
        with st.expander("ดูข้อมูลดิบทั้งหมด (หน่วย: °C, มม., %, กม./ชม., MJ/m²)"):
            st.dataframe(w)
    except Exception as e:
        st.error(f"ดึงข้อมูลอากาศไม่สำเร็จ ลองใหม่อีกครั้ง (สาเหตุ: {e})")

# ---------- แท็บ 2: สภาพอากาศเชียงใหม่ เดือนมีนาคม ----------
with แท็บอากาศมีนา:
    st.subheader("ข้อมูลสภาพอากาศ จ.เชียงใหม่ ประจำเดือนมีนาคม (Historical Archive)")
    st.caption("พิกัด จ.เชียงใหม่ (Lat: 18.79, Lon: 98.98) — ข้อมูลย้อนหลังตลอดทั้งเดือนมีนาคม")
    
    col_year, col_space = st.columns([1, 2])
    เลือกปี = col_year.selectbox("เลือกปี พ.ศ. (ค.ศ.) ที่ต้องการดู", [2024, 2023, 2022, 2021], index=0)
    
    try:
        w_march = ดึงอากาศเชียงใหม่เดือนมีนาคม(เลือกปี)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("อุณหภูมิสูงสุดเฉลี่ย", f"{w_march['สูงสุด'].mean():.1f} °C")
        m2.metric("อุณหภูมิต่ำสุดเฉลี่ย", f"{w_march['ต่ำสุด'].mean():.1f} °C")
        m3.metric("ฝนตกสะสมรวมทั้งเดือน", f"{w_march['ฝน'].sum():.1f} มม.")
        m4.metric("ความชื้นเฉลี่ยทั้งเดือน", f"{w_march['ความชื้น'].mean():.1f} %")
        
        st.write(f"กราฟแนวโน้มอุณหภูมิ (°C) เดือนมีนาคม ปี {เลือกปี}")
        st.line_chart(w_march.set_index("วันที่")[["สูงสุด", "ต่ำสุด"]])
        
        st.write(f"ปริมาณฝนรายวัน (มม.) เดือนมีนาคม ปี {เลือกปี}")
        st.bar_chart(w_march.set_index("วันที่")["ฝน"])
        
        with st.expander(f"ดูข้อมูลดิบสภาพอากาศเชียงใหม่ มีนาคม {เลือกปี} ทั้งหมด (31 วัน)"):
            st.dataframe(w_march, use_container_width=True)
    except Exception as e:
        st.error(f"ดึงข้อมูลสภาพอากาศเดือนมีนาคมไม่สำเร็จ (สาเหตุ: {e})")

# ---------- แท็บ 3: ระดับน้ำแม่น้ำ (flood API) ----------
with แท็บน้ำ:
    st.subheader("ปริมาณการไหลของแม่น้ำ (เตือนภัยน้ำท่วม)")
    c1, c2 = st.columns(2)
    lat2 = c1.number_input("ละติจูด (จุดใกล้แม่น้ำ)", value=18.79, key="lat_river")
    lon2 = c2.number_input("ลองจิจูด (จุดใกล้แม่น้ำ)", value=98.98, key="lon_river")
    try:
        r = ดึงระดับน้ำ(lat2, lon2)
        st.write("ปริมาณการไหล (ลูกบาศก์เมตร/วินาที)")
        st.line_chart(r.set_index("วันที่")["ปริมาณน้ำ"])
        st.info("ยิ่งค่าสูง = น้ำในแม่น้ำยิ่งมาก/เสี่ยงท่วม (เป็นปริมาณการไหล ไม่ใช่ระดับเป็นเมตร)")
        with st.expander("ดูข้อมูลดิบทั้งหมด"):
            st.dataframe(r)
    except Exception as e:
        st.error(f"ดึงระดับน้ำไม่สำเร็จ ลองใหม่อีกครั้ง (สาเหตุ: {e})")

# ---------- แท็บ 4: ราคาสินค้าเกษตร (เชียงใหม่) ----------
with แท็บราคา:
    st.subheader("ราคาสินค้าเกษตรจริง จ.เชียงใหม่ (ข้อมูลเปิดภาครัฐ)")
    ราคา, สด = ดึงราคาเกษตร()
    if not สด:
        st.warning("ตอนนี้เซิร์ฟเวอร์เข้า data.go.th ไม่ได้ "
                   "(มักถูกบล็อกจาก IP ดาต้าเซ็นเตอร์) — แสดงราคาสำรองสินค้าเกษตร จ.เชียงใหม่ แทน")
        st.write("ราคาล่าสุด (บาท/กก.)")
        st.bar_chart(ราคาสำรอง.set_index("สินค้า")["ราคา"])
        st.dataframe(ราคาสำรอง, hide_index=True)
    else:
        ปีล่าสุด = int(ราคา["ปี"].max())
        สินค้าทั้งหมด = sorted(ราคา["สินค้า"].dropna().unique())
        ค่าเริ่ม = [s for s in ["ลำไยอบแห้งเกรด AA", "ส้มสายน้ำผึ้งคละ", "สตรอว์เบอร์รีพระราชทาน 80", "ลิ้นจี่ฮงฮวย", "ทุเรียนหมอนทองคละ"]
                   if s in สินค้าทั้งหมด]
        if not ค่าเริ่ม and สินค้าทั้งหมด:
            ค่าเริ่ม = สินค้าทั้งหมด[:3]
            
        เลือก = st.multiselect("เลือกสินค้าที่จะดู", สินค้าทั้งหมด, default=ค่าเริ่ม)
        st.caption(f"ข้อมูลล่าสุดปี พ.ศ. {ปีล่าสุด} — สถิติทางการรายเดือน (จ.เชียงใหม่) หน่วย บาท/กก.")
        เดือนเรียง = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
                     "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
        if เลือก:
            ปีนี้ = ราคา[(ราคา["ปี"] == ปีล่าสุด) & (ราคา["สินค้า"].isin(เลือก))].copy()
            ปีนี้["เดือน"] = pd.Categorical(ปีนี้["เดือน"], categories=เดือนเรียง, ordered=True)
            ตาราง = ปีนี้.pivot_table(index="เดือน", columns="สินค้า",
                                     values="ราคา", observed=False)
            ตาราง = ตาราง.sort_index()
            ตาราง.index = ตาราง.index.astype(str)
            st.line_chart(ตาราง)
            เดือนล่าสุด = ตาราง.dropna(how="all").index[-1]
            st.write(f"ราคาเดือนล่าสุด ({เดือนล่าสุด} {ปีล่าสุด}) หน่วย บาท/กก.")
            แถวล่าสุด = ตาราง.loc[[เดือนล่าสุด]].T
            แถวล่าสุด.columns = ["ราคา"]
            st.dataframe(แถวล่าสุด)
        else:
            st.warning("เลือกสินค้าอย่างน้อย 1 อย่าง")