import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime
from PIL import Image
import warnings

# --- 1. SILENCE WARNINGS ---
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 2. CONFIG ---
st.set_page_config(page_title="Hedrick Wine Butler", page_icon="🍷")

# --- 3. CONNECTION REPAIR ---
def get_butler_connection():
    # Attempt to fix the PEM key in the background
    try:
        # We don't pass arguments here anymore to avoid the "unexpected argument" errors.
        # We rely on the library reading the [connections.gsheets] secrets.
        # But we check them first to warn the user.
        if "connections" not in st.secrets:
            st.error("Secrets are missing the [connections.gsheets] section.")
            return None
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"The Butler is having trouble with the cellar book: {e}")
        return None

# --- 4. INITIALIZE ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")
conn = get_butler_connection()

# --- 5. UI ---
st.title("🍷 Hedrick Wine Butler")
st.markdown("### *Your cellar assistant is ready.*")

# Camera and Upload
cam = st.camera_input("📸 Scan Label")
upload = st.file_uploader("📂 Or Upload", type=['jpg', 'png', 'jpeg'])
img_file = cam if cam else upload

st.write("---")
# Star rating (0-4 converted to 1-5)
rating = st.feedback("stars")

if st.button("Consult the Butler", type="primary"):
    if img_file and conn is not None:
        with st.spinner("The Butler is examining the vintage..."):
            try:
                # Process Image
                img = Image.open(img_file)
                
                # Instruction
                prompt = """
                Analyze this wine label. Return ONLY a JSON object: 
                {"Winery": str, "Wine_Name": str, "Vintage": str, "Varietal": str, "Region": str, "Butler_Comment": str}
                """
                
                response = model.generate_content([prompt, img])
                
                # Clean JSON
                res_text = response.text.strip()
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0]
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].split("```")[0]
                
                data = json.loads(res_text.strip())
                
                # --- DISPLAY ---
                st.subheader(f"{data.get('Winery')} - {data.get('Wine_Name')}")
                st.info(data.get('Butler_Comment'))
                
                # --- SAVE TO SHEET ---
                new_row = {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Winery": data.get("Winery"),
                    "Wine_Name": data.get("Wine_Name"),
                    "Vintage": data.get("Vintage"),
                    "Varietal": data.get("Varietal"),
                    "Region": data.get("Region"),
                    "User_Rating": (rating + 1) if rating is not None else 0,
                    "Butler_Comment": data.get("Butler_Comment")
                }
                
                # Defensive Reading: Handle case where sheet might be totally empty
                try:
                    existing_df = conn.read(ttl=0)
                except:
                    # If reading fails, create an empty dataframe with your headers
                    existing_df = pd.DataFrame(columns=[
                        "Timestamp", "Winery", "Wine_Name", "Vintage", 
                        "Varietal", "Region", "User_Rating", "Butler_Comment"
                    ])

                # Append and Update
                updated_df = pd.concat([existing_df, pd.DataFrame([new_row])], ignore_index=True)
                conn.update(data=updated_df)
                
                st.success("The Butler has recorded this in your Cellar Book!")
                st.toast("Cellar updated.", icon="🍷")
                
            except Exception as e:
                st.error(f"The Butler encountered an issue: {e}")
    elif conn is None:
        st.error("Connection failed. Check your Streamlit Secrets.")
    else:
        st.warning("Please provide an image.")

st.caption("Hedrick Wine Butler | v1.5")
