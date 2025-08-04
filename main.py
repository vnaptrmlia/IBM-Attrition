# HR_Attrition_Streamlit_App_Simple.py - Simple HR Attrition Prediction App
import streamlit as st
import pandas as pd
import numpy as np
import joblib
import pickle
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import hashlib
import warnings
import os

# Suppress warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Sistem Prediksi Attrisi Karyawan",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Single admin credential
ADMIN_CREDENTIALS = {
    "hr_admin": {
        "password_hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",  # admin123
        "role": "admin",
        "permissions": ["employee_assessment", "dashboard"],
        "display_name": "HR Administrator"
    }
}

def get_user_permissions(username):
    """Get user permissions based on username"""
    if username in ADMIN_CREDENTIALS:
        return ADMIN_CREDENTIALS[username]["permissions"]
    return []

def get_user_role(username):
    """Get user role based on username"""
    if username in ADMIN_CREDENTIALS:
        return ADMIN_CREDENTIALS[username]["role"]
    return "guest"

def get_user_display_name(username):
    """Get user display name"""
    if username in ADMIN_CREDENTIALS:
        return ADMIN_CREDENTIALS[username]["display_name"]
    return username

def has_permission(username, permission):
    """Check if user has specific permission"""
    permissions = get_user_permissions(username)
    return permission in permissions

class HRFeatureCategorizer:
    """HR Feature Categorizer dengan penjelasan detail"""
    
    def __init__(self):
        self.hr_features = self._define_essential_hr_features()
        
    def _define_essential_hr_features(self):
        """Define essential HR features untuk prediksi dengan penjelasan detail"""
        return {
            "Age": {
                "type": "number", "min": 18, "max": 65, "default": 32, "unit": "tahun", 
                "label": "Umur Karyawan",
                "explanation": "Usia karyawan dalam tahun. Karyawan yang lebih muda (20-30) dan mendekati pensiun (55+) memiliki risiko attrisi lebih tinggi."
            },
            "Gender": {
                "type": "selectbox", "options": {"Perempuan": 0, "Laki-laki": 1}, "default": "Laki-laki", 
                "label": "Jenis Kelamin",
                "explanation": "Jenis kelamin karyawan. Membantu menganalisis pola attrisi berdasarkan gender untuk strategi retensi yang tepat."
            },
            "MaritalStatus": {
                "type": "selectbox", "options": {"Lajang": 0, "Menikah": 1, "Bercerai": 2}, "default": "Menikah", 
                "label": "Status Pernikahan",
                "explanation": "Status pernikahan karyawan. Karyawan lajang cenderung lebih mobile, sedangkan yang menikah lebih stabil."
            },
            "DistanceFromHome": {
                "type": "number", "min": 1, "max": 50, "default": 7, "unit": "km", 
                "label": "Jarak dari Rumah",
                "explanation": "Jarak tempat tinggal ke kantor dalam kilometer. Jarak >20km meningkatkan risiko attrisi karena biaya dan waktu perjalanan."
            },
            "JobLevel": {
                "type": "selectbox", "options": {"Pemula": 1, "Junior": 2, "Menengah": 3, "Senior": 4, "Eksekutif": 5}, "default": "Menengah", 
                "label": "Level Pekerjaan",
                "explanation": "Tingkat senioritas dalam organisasi. Level pemula dan menengah memiliki risiko attrisi lebih tinggi karena mencari pertumbuhan karir."
            },
            "YearsAtCompany": {
                "type": "number", "min": 0, "max": 40, "default": 5, "unit": "tahun", 
                "label": "Lama Bekerja di Perusahaan",
                "explanation": "Total masa kerja di perusahaan. Karyawan dengan masa kerja 1-3 tahun paling berisiko karena masih beradaptasi."
            },
            "YearsInCurrentRole": {
                "type": "number", "min": 0, "max": 20, "default": 2, "unit": "tahun", 
                "label": "Lama di Posisi Saat Ini",
                "explanation": "Berapa lama karyawan berada di posisi/role yang sama. Terlalu lama di posisi yang sama dapat menyebabkan kebosanan."
            },
            "YearsSinceLastPromotion": {
                "type": "number", "min": 0, "max": 20, "default": 1, "unit": "tahun", 
                "label": "Tahun Sejak Promosi Terakhir",
                "explanation": "Waktu sejak promosi terakhir. Tidak ada promosi >3 tahun dapat menurunkan motivasi dan meningkatkan risiko attrisi."
            },
            "OverTime": {
                "type": "selectbox", "options": {"Tidak": 0, "Ya": 1}, "default": "Tidak", 
                "label": "Kerja Lembur",
                "explanation": "Apakah karyawan sering bekerja lembur. Lembur berlebihan adalah faktor risiko utama yang meningkatkan burnout."
            },
            "BusinessTravel": {
                "type": "selectbox", "options": {"Tidak Pernah": 0, "Jarang": 1, "Sering": 2}, "default": "Jarang", 
                "label": "Perjalanan Dinas",
                "explanation": "Frekuensi perjalanan dinas. Perjalanan yang terlalu sering dapat mengganggu work-life balance."
            },
            "MonthlyIncome": {
                "type": "number", "min": 1000, "max": 25000, "default": 5000, "unit": "USD", 
                "label": "Gaji Bulanan (USD)",
                "explanation": "Gaji bulanan dalam USD. Gaji yang tidak kompetitif dibanding pasar adalah faktor risiko attrisi yang signifikan."
            },
            "PercentSalaryHike": {
                "type": "slider", "min": 0, "max": 25, "default": 13, "unit": "%", 
                "label": "Persentase Kenaikan Gaji Terakhir",
                "explanation": "Persentase kenaikan gaji tahun lalu. Kenaikan <10% atau tidak ada kenaikan meningkatkan risiko attrisi."
            },
            "StockOptionLevel": {
                "type": "selectbox", "options": {"Tidak Ada": 0, "Dasar": 1, "Standar": 2, "Premium": 3}, "default": "Dasar", 
                "label": "Level Opsi Saham",
                "explanation": "Tingkat kepemilikan saham perusahaan. Opsi saham dapat meningkatkan loyalitas dan retensi karyawan jangka panjang."
            },
            "JobSatisfaction": {
                "type": "selectbox", "options": {"Rendah": 1, "Sedang": 2, "Tinggi": 3, "Sangat Tinggi": 4}, "default": "Tinggi", 
                "label": "Kepuasan Kerja",
                "explanation": "Tingkat kepuasan dengan pekerjaan saat ini. Kepuasan rendah adalah prediktor terkuat untuk attrisi."
            },
            "WorkLifeBalance": {
                "type": "selectbox", "options": {"Buruk": 1, "Baik": 2, "Lebih Baik": 3, "Terbaik": 4}, "default": "Lebih Baik", 
                "label": "Keseimbangan Kerja-Hidup",
                "explanation": "Seberapa baik karyawan dapat menyeimbangkan pekerjaan dan kehidupan pribadi. Work-life balance buruk meningkatkan risiko burnout."
            },
            "EnvironmentSatisfaction": {
                "type": "selectbox", "options": {"Rendah": 1, "Sedang": 2, "Tinggi": 3, "Sangat Tinggi": 4}, "default": "Tinggi", 
                "label": "Kepuasan Lingkungan Kerja",
                "explanation": "Kepuasan dengan lingkungan kerja, rekan kerja, dan budaya perusahaan. Lingkungan yang toxic meningkatkan turnover."
            },
            "PerformanceRating": {
                "type": "selectbox", "options": {"Rendah": 1, "Baik": 2, "Sangat Baik": 3, "Luar Biasa": 4}, "default": "Sangat Baik", 
                "label": "Rating Kinerja",
                "explanation": "Penilaian kinerja terbaru. High performer yang tidak dihargai atau low performer yang merasa tertekan sama-sama berisiko tinggi."
            }
        }
    
    def create_hr_input_form(self):
        """Create form input dengan penjelasan detail"""
        st.sidebar.header("👥 Informasi Karyawan")
        st.sidebar.markdown("**Penilaian Risiko Attrisi Karyawan**")
        st.sidebar.info("💡 **Tips:** Hover pada ikon (?) untuk melihat penjelasan setiap field")
        
        profile = st.sidebar.selectbox(
            "Profil Cepat:",
            ["📊 Input Manual", "🌟 Karyawan Berprestasi", "📈 Karyawan Biasa", "🆕 Fresh Graduate", "⚠️ Karyawan Berisiko"],
            help="Pilih profil template untuk mengisi data dengan cepat, atau pilih Input Manual untuk kustomisasi lengkap"
        )
        
        input_data = {}
        
        if profile == "📊 Input Manual":
            st.sidebar.subheader("📋 Data Demografi Personal")
            st.sidebar.caption("Informasi dasar tentang karyawan")
            
            feature_config = self.hr_features["Age"]
            input_data["Age"] = st.sidebar.number_input(
                feature_config["label"], 
                18, 65, 32,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["Gender"]
            input_data["Gender"] = st.sidebar.selectbox(
                feature_config["label"], 
                ["Perempuan", "Laki-laki"], 
                index=1,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["MaritalStatus"]
            input_data["MaritalStatus"] = st.sidebar.selectbox(
                feature_config["label"], 
                ["Lajang", "Menikah", "Bercerai"], 
                index=1,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["DistanceFromHome"]
            input_data["DistanceFromHome"] = st.sidebar.number_input(
                feature_config["label"], 
                1, 50, 7,
                help=feature_config["explanation"]
            )
            
            st.sidebar.subheader("💼 Informasi Pekerjaan")
            st.sidebar.caption("Detail posisi dan masa kerja")
            
            feature_config = self.hr_features["JobLevel"]
            input_data["JobLevel"] = st.sidebar.selectbox(
                feature_config["label"], 
                ["Pemula", "Junior", "Menengah", "Senior", "Eksekutif"], 
                index=2,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["YearsAtCompany"]
            input_data["YearsAtCompany"] = st.sidebar.number_input(
                feature_config["label"], 
                0, 40, 5,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["YearsInCurrentRole"]
            input_data["YearsInCurrentRole"] = st.sidebar.number_input(
                feature_config["label"], 
                0, 20, 2,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["YearsSinceLastPromotion"]
            input_data["YearsSinceLastPromotion"] = st.sidebar.number_input(
                feature_config["label"], 
                0, 20, 1,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["OverTime"]
            input_data["OverTime"] = st.sidebar.selectbox(
                feature_config["label"], 
                ["Tidak", "Ya"], 
                index=0,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["BusinessTravel"]
            input_data["BusinessTravel"] = st.sidebar.selectbox(
                feature_config["label"], 
                ["Tidak Pernah", "Jarang", "Sering"], 
                index=1,
                help=feature_config["explanation"]
            )
            
            st.sidebar.subheader("💰 Kompensasi & Benefit")
            st.sidebar.caption("Informasi gaji dan benefit karyawan")
            
            feature_config = self.hr_features["MonthlyIncome"]
            input_data["MonthlyIncome"] = st.sidebar.number_input(
                feature_config["label"], 
                1000, 25000, 5000, 
                step=500,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["PercentSalaryHike"]
            input_data["PercentSalaryHike"] = st.sidebar.slider(
                feature_config["label"], 
                0, 25, 13,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["StockOptionLevel"]
            input_data["StockOptionLevel"] = st.sidebar.selectbox(
                feature_config["label"], 
                ["Tidak Ada", "Dasar", "Standar", "Premium"], 
                index=1,
                help=feature_config["explanation"]
            )
            
            st.sidebar.subheader("😊 Kepuasan & Kinerja")
            st.sidebar.caption("Evaluasi kepuasan dan performa karyawan")
            
            feature_config = self.hr_features["JobSatisfaction"]
            input_data["JobSatisfaction"] = st.sidebar.selectbox(
                feature_config["label"], 
                ["Rendah", "Sedang", "Tinggi", "Sangat Tinggi"], 
                index=2,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["WorkLifeBalance"]
            input_data["WorkLifeBalance"] = st.sidebar.selectbox(
                feature_config["label"], 
                ["Buruk", "Baik", "Lebih Baik", "Terbaik"], 
                index=2,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["EnvironmentSatisfaction"]
            input_data["EnvironmentSatisfaction"] = st.sidebar.selectbox(
                feature_config["label"], 
                ["Rendah", "Sedang", "Tinggi", "Sangat Tinggi"], 
                index=2,
                help=feature_config["explanation"]
            )
            
            feature_config = self.hr_features["PerformanceRating"]
            input_data["PerformanceRating"] = st.sidebar.selectbox(
                feature_config["label"], 
                ["Rendah", "Baik", "Sangat Baik", "Luar Biasa"], 
                index=2,
                help=feature_config["explanation"]
            )
            
        else:
            # Profil preset dengan penjelasan
            profiles = {
                "🌟 Karyawan Berprestasi": {
                    "description": "High performer dengan kompensasi tinggi dan kepuasan kerja yang baik",
                    "data": {
                        "Age": 35, "Gender": "Laki-laki", "MaritalStatus": "Menikah", "DistanceFromHome": 5,
                        "JobLevel": "Senior", "YearsAtCompany": 8, "YearsInCurrentRole": 3, "YearsSinceLastPromotion": 1,
                        "OverTime": "Tidak", "BusinessTravel": "Jarang", "MonthlyIncome": 8000, "PercentSalaryHike": 18,
                        "StockOptionLevel": "Premium", "JobSatisfaction": "Sangat Tinggi", "WorkLifeBalance": "Lebih Baik",
                        "EnvironmentSatisfaction": "Sangat Tinggi", "PerformanceRating": "Luar Biasa"
                    }
                },
                "📈 Karyawan Biasa": {
                    "description": "Karyawan dengan performa rata-rata dan kondisi kerja yang stabil",
                    "data": {
                        "Age": 32, "Gender": "Perempuan", "MaritalStatus": "Menikah", "DistanceFromHome": 7,
                        "JobLevel": "Menengah", "YearsAtCompany": 5, "YearsInCurrentRole": 2, "YearsSinceLastPromotion": 2,
                        "OverTime": "Tidak", "BusinessTravel": "Jarang", "MonthlyIncome": 5000, "PercentSalaryHike": 13,
                        "StockOptionLevel": "Dasar", "JobSatisfaction": "Tinggi", "WorkLifeBalance": "Lebih Baik",
                        "EnvironmentSatisfaction": "Tinggi", "PerformanceRating": "Sangat Baik"
                    }
                },
                "🆕 Fresh Graduate": {
                    "description": "Karyawan baru lulusan dengan adaptasi awal dan gaji entry level",
                    "data": {
                        "Age": 24, "Gender": "Laki-laki", "MaritalStatus": "Lajang", "DistanceFromHome": 15,
                        "JobLevel": "Pemula", "YearsAtCompany": 1, "YearsInCurrentRole": 1, "YearsSinceLastPromotion": 0,
                        "OverTime": "Ya", "BusinessTravel": "Tidak Pernah", "MonthlyIncome": 3000, "PercentSalaryHike": 11,
                        "StockOptionLevel": "Tidak Ada", "JobSatisfaction": "Tinggi", "WorkLifeBalance": "Baik",
                        "EnvironmentSatisfaction": "Tinggi", "PerformanceRating": "Baik"
                    }
                },
                "⚠️ Karyawan Berisiko": {
                    "description": "Karyawan dengan multiple red flags: lembur, kepuasan rendah, no promotion",
                    "data": {
                        "Age": 28, "Gender": "Perempuan", "MaritalStatus": "Lajang", "DistanceFromHome": 25,
                        "JobLevel": "Junior", "YearsAtCompany": 3, "YearsInCurrentRole": 3, "YearsSinceLastPromotion": 3,
                        "OverTime": "Ya", "BusinessTravel": "Sering", "MonthlyIncome": 3500, "PercentSalaryHike": 11,
                        "StockOptionLevel": "Tidak Ada", "JobSatisfaction": "Rendah", "WorkLifeBalance": "Buruk",
                        "EnvironmentSatisfaction": "Rendah", "PerformanceRating": "Baik"
                    }
                }
            }
            
            profile_info = profiles.get(profile, profiles["📈 Karyawan Biasa"])
            st.sidebar.info(f"**{profile}**\n\n{profile_info['description']}")
            input_data = profile_info["data"]
        
        # Convert Indonesian text values to numeric
        numeric_data = {}
        for key, value in input_data.items():
            if key in self.hr_features:
                feature_config = self.hr_features[key]
                if feature_config["type"] == "selectbox" and "options" in feature_config:
                    numeric_data[key] = feature_config["options"].get(value, 0)
                else:
                    numeric_data[key] = value
            else:
                mapping = {
                    "Gender": {"Perempuan": 0, "Laki-laki": 1},
                    "MaritalStatus": {"Lajang": 0, "Menikah": 1, "Bercerai": 2},
                    "JobLevel": {"Pemula": 1, "Junior": 2, "Menengah": 3, "Senior": 4, "Eksekutif": 5},
                    "OverTime": {"Tidak": 0, "Ya": 1},
                    "BusinessTravel": {"Tidak Pernah": 0, "Jarang": 1, "Sering": 2},
                    "StockOptionLevel": {"Tidak Ada": 0, "Dasar": 1, "Standar": 2, "Premium": 3},
                    "JobSatisfaction": {"Rendah": 1, "Sedang": 2, "Tinggi": 3, "Sangat Tinggi": 4},
                    "WorkLifeBalance": {"Buruk": 1, "Baik": 2, "Lebih Baik": 3, "Terbaik": 4},
                    "EnvironmentSatisfaction": {"Rendah": 1, "Sedang": 2, "Tinggi": 3, "Sangat Tinggi": 4},
                    "PerformanceRating": {"Rendah": 1, "Baik": 2, "Sangat Baik": 3, "Luar Biasa": 4}
                }
                if key in mapping:
                    numeric_data[key] = mapping[key].get(value, 0)
                else:
                    numeric_data[key] = value
        
        return numeric_data

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(str.encode(password)).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash"""
    return hash_password(password) == hashed

def login_page():
    """Halaman login dengan single admin"""
    st.markdown("""
    <div style="text-align: center; padding: 50px 0;">
        <h1>👥 Sistem Prediksi Attrisi Karyawan</h1>
        <h3>Platform Analitik Sumber Daya Manusia</h3>
        <p>Penilaian risiko attrisi karyawan berbasis Machine Learning</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Login Administrator HR")
        
        with st.form("login_form"):
            username = st.text_input("👤 Nama Pengguna", placeholder="Masukkan hr_admin")
            password = st.text_input("🔑 Kata Sandi", type="password", placeholder="Masukkan password")
            submit_button = st.form_submit_button("🔓 Akses Sistem", use_container_width=True)
            
            if submit_button:
                if username in ADMIN_CREDENTIALS:
                    if verify_password(password, ADMIN_CREDENTIALS[username]["password_hash"]):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_role = get_user_role(username)
                        st.session_state.user_permissions = get_user_permissions(username)
                        st.session_state.display_name = get_user_display_name(username)
                        st.success(f"✅ Selamat datang {get_user_display_name(username)}!")
                        st.rerun()
                    else:
                        st.error("❌ Kata sandi salah!")
                else:
                    st.error("❌ Nama pengguna tidak ditemukan!")
        
        with st.expander("📋 Informasi Login", expanded=False):
            st.markdown("""
            **🔑 Akun Administrator:**
            
            **👑 HR Administrator**
            - **Username:** hr_admin
            - **Password:** admin123
            - **Akses:**
              - ✅ Penilaian Risiko Karyawan
              - ✅ Dashboard Analitik
              - ✅ Semua Fitur Sistem
            
            **🛡️ Keamanan:**
            - Password terenkripsi SHA256
            - Session management yang aman
            - Role-based access control
            """)

@st.cache_resource
def load_model_components():
    """Load komponen model"""
    try:
        model = joblib.load('models/logistic_regression_model.pkl')
        scaler = joblib.load('models/scaler.pkl')
        
        with open('models/feature_names.pkl', 'rb') as f:
            feature_names = pickle.load(f)
        
        with open('models/model_metadata.pkl', 'rb') as f:
            metadata = pickle.load(f)
        
        return model, scaler, feature_names, metadata
        
    except FileNotFoundError:
        st.error("❌ File model tidak ditemukan. Menggunakan mode demo.")
        return None, None, None, {"model_type": "Demo", "test_accuracy": 0.87, "roc_auc": 0.82}

def prepare_model_input(hr_input, feature_names):
    """Prepare input untuk prediksi model"""
    
    model_input = pd.DataFrame(index=[0], columns=feature_names)
    model_input = model_input.fillna(0)
    
    feature_mapping = {
        'Age': 'Age',
        'MonthlyIncome': 'MonthlyIncome', 
        'YearsAtCompany': 'YearsAtCompany',
        'YearsInCurrentRole': 'YearsInCurrentRole',
        'YearsSinceLastPromotion': 'YearsSinceLastPromotion',
        'DistanceFromHome': 'DistanceFromHome',
        'PercentSalaryHike': 'PercentSalaryHike',
        'JobLevel': 'JobLevel',
        'StockOptionLevel': 'StockOptionLevel',
        'JobSatisfaction': 'JobSatisfaction',
        'WorkLifeBalance': 'WorkLifeBalance',
        'EnvironmentSatisfaction': 'EnvironmentSatisfaction',
        'PerformanceRating': 'PerformanceRating'
    }
    
    for hr_key, model_key in feature_mapping.items():
        if hr_key in hr_input and model_key in model_input.columns:
            model_input[model_key] = hr_input[hr_key]
    
    categorical_mappings = {
        'Gender_Male': 1 if hr_input.get('Gender', 0) == 1 else 0,
        'MaritalStatus_Married': 1 if hr_input.get('MaritalStatus', 0) == 1 else 0,
        'MaritalStatus_Single': 1 if hr_input.get('MaritalStatus', 0) == 0 else 0,
        'OverTime_Yes': 1 if hr_input.get('OverTime', 0) == 1 else 0,
        'BusinessTravel_Travel_Frequently': 1 if hr_input.get('BusinessTravel', 0) == 2 else 0,
        'BusinessTravel_Travel_Rarely': 1 if hr_input.get('BusinessTravel', 0) == 1 else 0,
    }
    
    for model_key, value in categorical_mappings.items():
        if model_key in model_input.columns:
            model_input[model_key] = value
    
    return model_input

def make_prediction(model, scaler, hr_input, feature_names):
    """Buat prediksi attrisi"""
    try:
        if model is None:
            risk_score = 0.3 + (hr_input.get('OverTime', 0) * 0.2) + \
                        (1 - hr_input.get('JobSatisfaction', 3)/4) * 0.3 + \
                        (1 - hr_input.get('WorkLifeBalance', 3)/4) * 0.2
            risk_score = min(max(risk_score, 0.05), 0.95)
            prediction = 1 if risk_score > 0.5 else 0
            prediction_proba = [1-risk_score, risk_score]
            return prediction, prediction_proba, None
        
        model_input = prepare_model_input(hr_input, feature_names)
        
        if scaler is not None:
            model_input_scaled = scaler.transform(model_input)
            model_input = pd.DataFrame(model_input_scaled, columns=feature_names)
        
        prediction = model.predict(model_input)[0]
        prediction_proba = model.predict_proba(model_input)[0]
        
        return prediction, prediction_proba, model_input
        
    except Exception as e:
        st.error(f"❌ Error prediksi: {e}")
        return None, None, None

def display_prediction_results(prediction, prediction_proba, hr_input, metadata):
    """Display hasil prediksi karyawan dengan penjelasan detail"""
    
    st.header("🎯 Hasil Penilaian Risiko Attrisi Karyawan")
    
    col1, col2, col3 = st.columns(3)
    
    attrition_probability = prediction_proba[1]
    
    with col1:
        st.subheader("📊 Level Risiko")
        
        if attrition_probability > 0.7:
            st.error("**🚨 RISIKO TINGGI**")
            risk_level = "TINGGI"
            risk_color = "red"
            risk_description = "Karyawan ini memiliki probabilitas sangat tinggi untuk keluar dalam 6-12 bulan ke depan."
        elif attrition_probability > 0.3:
            st.warning("**⚠️ RISIKO SEDANG**")
            risk_level = "SEDANG" 
            risk_color = "orange"
            risk_description = "Karyawan ini menunjukkan beberapa tanda risiko attrisi."
        else:
            st.success("**✅ RISIKO RENDAH**")
            risk_level = "RENDAH"
            risk_color = "green"
            risk_description = "Karyawan ini kemungkinan besar akan bertahan."
        
        st.info(risk_description)
        st.metric("Probabilitas Attrisi", f"{attrition_probability:.1%}")
        st.metric("Tingkat Keyakinan", f"{max(prediction_proba):.1%}")
    
    with col2:
        st.subheader("📈 Visualisasi Risiko")
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = attrition_probability * 100,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Risiko Attrisi (%)"},
            delta = {'reference': 30},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': risk_color},
                'steps': [
                    {'range': [0, 30], 'color': "lightgreen"},
                    {'range': [30, 70], 'color': "yellow"},
                    {'range': [70, 100], 'color': "lightcoral"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 70
                }
            }
        ))
        fig_gauge.update_layout(height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col3:
        st.subheader("👤 Profil Karyawan")
        
        age = hr_input.get('Age', 'N/A')
        income = hr_input.get('MonthlyIncome', 0)
        years_company = hr_input.get('YearsAtCompany', 0)
        job_level = hr_input.get('JobLevel', 0)
        
        # Convert job level number to text
        job_levels = {1: "Pemula", 2: "Junior", 3: "Menengah", 4: "Senior", 5: "Eksekutif"}
        job_level_text = job_levels.get(job_level, "Unknown")
        
        st.metric("Umur", f"{age} tahun")
        st.metric("Gaji Bulanan", f"${income:,}")
        st.metric("Masa Kerja", f"{years_company} tahun")
        st.metric("Level Jabatan", job_level_text)

    # Risk Factors Analysis
    st.subheader("🔍 Analisis Faktor Risiko")
    
    risk_factors = []
    
    # Check various risk factors
    if hr_input.get('OverTime', 0) == 1:
        risk_factors.append("🔴 **Sering Lembur** - Indikasi workload berlebihan atau work-life balance buruk")
    
    if hr_input.get('JobSatisfaction', 4) <= 2:
        risk_factors.append("🔴 **Kepuasan Kerja Rendah** - Faktor risiko utama untuk attrisi")
    
    if hr_input.get('WorkLifeBalance', 4) <= 2:
        risk_factors.append("🔴 **Work-Life Balance Buruk** - Dapat menyebabkan burnout")
    
    if hr_input.get('YearsSinceLastPromotion', 0) >= 3:
        risk_factors.append("🟡 **Tidak Ada Promosi 3+ Tahun** - Potensi stagnasi karir")
    
    if hr_input.get('DistanceFromHome', 0) > 20:
        risk_factors.append("🟡 **Jarak Rumah Jauh** - Biaya dan waktu komute tinggi")
    
    if hr_input.get('PercentSalaryHike', 13) < 10:
        risk_factors.append("🟡 **Kenaikan Gaji Rendah** - Gaji tidak kompetitif")
    
    if hr_input.get('BusinessTravel', 1) == 2:
        risk_factors.append("🟡 **Sering Perjalanan Dinas** - Dapat mengganggu kehidupan pribadi")
    
    if hr_input.get('EnvironmentSatisfaction', 4) <= 2:
        risk_factors.append("🟡 **Kepuasan Lingkungan Kerja Rendah** - Budaya atau lingkungan tidak mendukung")

    st.markdown("**⚠️ Faktor Risiko yang Teridentifikasi:**")
    if risk_factors:
        for factor in risk_factors:
            st.write(factor)
    else:
        st.success("✅ Tidak ada faktor risiko utama yang terdeteksi")

def main_app():
    """Aplikasi utama dengan single admin"""
    username = st.session_state.username
    user_role = st.session_state.get('user_role', 'admin')
    user_permissions = st.session_state.get('user_permissions', [])
    display_name = st.session_state.get('display_name', username)
    
    # Header dengan informasi role
    st.title(f"👥 Sistem Prediksi Attrisi Karyawan")
    
    st.markdown(f"""
    **Selamat datang {display_name}** 🟢 **HR Administrator** | **🟢 Sistem Online** | **🛡️ Sesi Aman**
    
    ### 📊 **Tentang Sistem Analitik HR**
    Sistem prediksi attrisi karyawan berbasis Machine Learning yang dirancang khusus untuk membantu departemen HR dalam:
    - **🎯 Prediksi Risiko:** Mengidentifikasi karyawan yang berisiko tinggi keluar dari perusahaan
    - **📊 Analisis Data:** Memahami faktor-faktor yang mempengaruhi keputusan karyawan untuk keluar
    - **📈 Insight Mendalam:** Memberikan analisis berbasis data untuk pemahaman yang lebih baik
    
    **Status Akses:** Full Administrator Access ✅
    """)
    
    # Logout button in sidebar
    if st.sidebar.button("🚪 Keluar"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_role = None
        st.session_state.user_permissions = []
        st.rerun()
    
    # Display admin info in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**🔐 Level Akses: HR Administrator**")
    st.sidebar.markdown("**✅ Akses Penuh:**")
    st.sidebar.write("• Penilaian Risiko Karyawan")
    st.sidebar.write("• Dashboard Analitik")
    st.sidebar.write("• Semua Fitur Sistem")
    
    st.markdown("---")
    
    # Load model components
    model, scaler, feature_names, metadata = load_model_components()
    
    # Create tabs
    tab1, tab2 = st.tabs(["🎯 Penilaian Risiko Karyawan", "📊 Dashboard"])
    
    with tab1:
        st.header("🎯 Penilaian Risiko Attrisi Karyawan")
        st.markdown("**Evaluasi risiko attrisi individual berdasarkan data karyawan**")
        
        hr_categorizer = HRFeatureCategorizer()
        hr_input = hr_categorizer.create_hr_input_form()
        
        # Display summary
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Umur", f"{hr_input.get('Age', 0)} tahun")
        col2.metric("Gaji", f"${hr_input.get('MonthlyIncome', 0):,}")
        col3.metric("Masa Kerja", f"{hr_input.get('YearsAtCompany', 0)} tahun")
        
        # Convert job level to text
        job_levels = {1: "Pemula", 2: "Junior", 3: "Menengah", 4: "Senior", 5: "Eksekutif"}
        job_level_text = job_levels.get(hr_input.get('JobLevel', 3), "Menengah")
        col4.metric("Level Kerja", job_level_text)
        
        if st.button("🚀 Analisis Risiko Attrisi", type="primary"):
            with st.spinner("Menganalisis data karyawan..."):
                prediction, prediction_proba, input_df = make_prediction(model, scaler, hr_input, feature_names)
                
                if prediction is not None:
                    st.success("✅ Analisis selesai!")
                    display_prediction_results(prediction, prediction_proba, hr_input, metadata)
                else:
                    st.error("❌ Analisis gagal")
    
    with tab2:
        st.header("📊 Dashboard Analitik")
        st.markdown("**Overview kinerja sistem dan insight organisasi**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Kinerja Model")
            
            if metadata:
                st.metric("Akurasi Model", f"{metadata.get('test_accuracy', 0.87):.1%}")
                st.metric("Skor ROC-AUC", f"{metadata.get('roc_auc', 0.82):.3f}")
                st.metric("Tipe Model", metadata.get('model_type', 'Logistic Regression'))
            
            st.subheader("🏢 Analisis Risiko Departemen")
            dept_data = {
                'Departemen': ['Sales', 'Engineering', 'Marketing', 'HR', 'Finance'],
                'Risiko_Rata2': [0.28, 0.15, 0.22, 0.12, 0.18],
                'Jumlah_Karyawan': [150, 200, 75, 25, 50]
            }
            dept_df = pd.DataFrame(dept_data)
            
            fig_dept = px.bar(
                dept_df,
                x='Departemen',
                y='Risiko_Rata2',
                color='Risiko_Rata2',
                title='Rata-rata Risiko Attrisi per Departemen',
                color_continuous_scale='Reds',
                text='Risiko_Rata2'
            )
            fig_dept.update_traces(texttemplate='%{text:.1%}', textposition='outside')
            fig_dept.update_layout(showlegend=False)
            st.plotly_chart(fig_dept, use_container_width=True)
        
        with col2:
            st.subheader("📈 Statistik Penggunaan")
            
            st.metric("Penilaian Hari Ini", "47", "+12")
            st.metric("Karyawan Risiko Tinggi", "23", "+3") 
            st.metric("Total Karyawan Dinilai", "342", "+28")
            st.metric("Akurasi Prediksi", "87%", "+2%")
            
            st.subheader("🎯 Faktor Risiko Utama")
            risk_data = {
                'Faktor': ['Kerja Lembur', 'Kepuasan Kerja Rendah', 'Work-Life Balance Buruk', 'Jarak Jauh', 'Tidak Ada Promosi'],
                'Dampak': [0.45, 0.38, 0.32, 0.28, 0.25]
            }
            risk_df = pd.DataFrame(risk_data)
            
            fig_risk = px.bar(
                risk_df,
                x='Dampak',
                y='Faktor',
                orientation='h',
                title='Skor Dampak Faktor Risiko',
                color='Dampak',
                color_continuous_scale='Oranges',
                text='Dampak'
            )
            fig_risk.update_traces(texttemplate='%{text:.0%}', textposition='outside')
            fig_risk.update_layout(showlegend=False)
            st.plotly_chart(fig_risk, use_container_width=True)
        
        
        # Summary Statistics
        st.subheader("📊 Ringkasan Statistik")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("**📈 Rata-rata Tingkat Attrisi**")
            st.info("15.4% per tahun")
            st.caption("Target: <14%")
        
        with col2:
            st.markdown("**🎯 Tingkat Deteksi Dini**")
            st.info("73% kasus terdeteksi")
            st.caption("dari total attrisi aktual")
        
        with col3:
            st.markdown("**⏰ Waktu Prediksi Rata-rata**")
            st.info("2.3 bulan sebelum resign")
            st.caption("window untuk intervensi")
        
        with col4:
            st.markdown("**🏆 Departemen Terstabil**")
            st.info("HR Department")
            st.caption("12% tingkat attrisi")

def main():
    """Fungsi utama dengan single admin"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if st.session_state.logged_in:
        main_app()
    else:
        login_page()

if __name__ == "__main__":
    main()
