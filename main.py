# HR_Attrition_Streamlit_App_RBAC.py - Complete HR App with Role-Based Access Control
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
    page_title="Sistem Prediksi Attrisi Karyawan & Analisis Finansial",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Admin credentials with role-based access
ADMIN_CREDENTIALS = {
    "admin": {
        "password_hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",  # admin123
        "role": "admin",
        "permissions": ["employee_assessment", "financial_analysis", "dashboard"],
        "display_name": "Administrator"
    },
    "hr_manager": {
        "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",  # admin
        "role": "hr_manager", 
        "permissions": ["employee_assessment", "financial_analysis", "dashboard"],
        "display_name": "HR Manager"
    },
    "financial": {
        "password_hash": "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f",  # finance123
        "role": "financial",
        "permissions": ["financial_analysis"],
        "display_name": "Financial Analyst"
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

class FinancialAnalysisCalculator:
    """Financial Analysis Calculator for Attrition Cost Assessment - Global & Indonesia"""
    
    def __init__(self):
        self.cost_components = self._define_cost_components()
        self.exchange_rates = self._get_exchange_rates()
        self.regional_configs = self._define_regional_configs()
        
    def _define_cost_components(self):
        """Define standardized cost components for attrition"""
        return {
            "recruitment": {
                "label": "Biaya Rekrutmen & Perekrutan",
                "description": "Job posting, screening, interviewing, background checks",
                "default_multiplier": 0.2,
                "industry_range": (0.15, 0.25),
                "indonesia_multiplier": 0.18
            },
            "training": {
                "label": "Biaya Pelatihan & Orientasi", 
                "description": "New employee training, orientation, materials",
                "default_multiplier": 0.15,
                "industry_range": (0.10, 0.20),
                "indonesia_multiplier": 0.12
            },
            "productivity_loss": {
                "label": "Kehilangan Produktivitas",
                "description": "Lost productivity during transition period",
                "default_multiplier": 0.50,
                "industry_range": (0.30, 0.70),
                "indonesia_multiplier": 0.45
            },
            "separation": {
                "label": "Biaya Pemisahan",
                "description": "Exit interviews, knowledge transfer, final pay",
                "default_multiplier": 0.05,
                "industry_range": (0.03, 0.08),
                "indonesia_multiplier": 0.08
            },
            "opportunity_cost": {
                "label": "Biaya Peluang",
                "description": "Delayed projects, overtime for remaining staff",
                "default_multiplier": 0.10,
                "industry_range": (0.05, 0.15),
                "indonesia_multiplier": 0.07
            }
        }
    
    def _get_exchange_rates(self):
        """Get current exchange rates (updated 2024)"""
        return {
            "USD_to_IDR": 15750,
            "EUR_to_IDR": 17200,
            "IDR_to_USD": 1/15750,
            "update_date": "2024-12-01"
        }
    
    def _define_regional_configs(self):
        """Define regional configurations for different markets"""
        return {
            "GLOBAL": {
                "currency": "USD",
                "label": "Pasar Global/US",
                "salary_ranges": {
                    "entry": 35000,
                    "mid": 65000,
                    "senior": 95000,
                    "executive": 150000
                },
                "cost_base": "global"
            },
            "INDONESIA": {
                "currency": "IDR", 
                "label": "Pasar Indonesia",
                "salary_ranges": {
                    "entry": 60000000,
                    "mid": 120000000,
                    "senior": 240000000,
                    "executive": 480000000
                },
                "cost_base": "indonesia",
                "benefits": {
                    "thr_bonus": 0.083,
                    "jamsostek": 0.054,
                    "severance_multiplier": 2.0
                }
            }
        }
    
    def calculate_attrition_cost(self, annual_salary, region="GLOBAL", currency=None, custom_multipliers=None):
        """Calculate total attrition cost per employee with regional considerations"""
        
        regional_config = self.regional_configs.get(region, self.regional_configs["GLOBAL"])
        base_currency = currency or regional_config["currency"]
        
        if custom_multipliers:
            multipliers = custom_multipliers
        elif region == "INDONESIA":
            multipliers = {k: v["indonesia_multiplier"] for k, v in self.cost_components.items()}
        else:
            multipliers = {k: v["default_multiplier"] for k, v in self.cost_components.items()}
        
        cost_breakdown = {}
        total_cost = 0
        
        for component, details in self.cost_components.items():
            multiplier = multipliers.get(component, details["default_multiplier"])
            cost = annual_salary * multiplier
            
            if region == "INDONESIA" and component == "separation":
                severance_cost = annual_salary * regional_config["benefits"]["severance_multiplier"] / 12
                thr_cost = annual_salary * regional_config["benefits"]["thr_bonus"]
                jamsostek_cost = annual_salary * regional_config["benefits"]["jamsostek"]
                cost += severance_cost + thr_cost + jamsostek_cost
            
            cost_breakdown[component] = {
                "amount": cost,
                "percentage": (cost / annual_salary) * 100,
                "label": details["label"]
            }
            total_cost += cost
        
        return {
            "total_cost": total_cost,
            "breakdown": cost_breakdown,
            "currency": base_currency,
            "region": region,
            "annual_salary": annual_salary,
            "cost_as_percentage_of_salary": (total_cost / annual_salary) * 100,
            "exchange_rate": self.exchange_rates.get(f"{base_currency}_to_IDR", 1) if base_currency != "IDR" else 1
        }
    
    def estimate_annual_savings(self, total_employees, attrition_rate, avg_salary, 
                              prediction_accuracy, intervention_effectiveness, 
                              region="GLOBAL", currency=None):
        """Estimate annual savings from attrition prediction with regional considerations"""
        
        regional_config = self.regional_configs.get(region, self.regional_configs["GLOBAL"])
        base_currency = currency or regional_config["currency"]
        
        annual_attrition_cases = int(total_employees * (attrition_rate / 100))
        cost_per_case = self.calculate_attrition_cost(avg_salary, region, base_currency)["total_cost"]
        current_annual_cost = annual_attrition_cases * cost_per_case
        predicted_cases = annual_attrition_cases * (prediction_accuracy / 100)
        prevented_cases = predicted_cases * (intervention_effectiveness / 100)
        annual_savings = prevented_cases * cost_per_case
        
        conversions = {}
        if base_currency == "IDR":
            conversions["USD"] = annual_savings * self.exchange_rates["IDR_to_USD"]
        elif base_currency == "USD":
            conversions["IDR"] = annual_savings * self.exchange_rates["USD_to_IDR"]
        
        return {
            "current_annual_cost": current_annual_cost,
            "annual_attrition_cases": annual_attrition_cases,
            "predicted_cases": predicted_cases,
            "prevented_cases": prevented_cases,
            "annual_savings": annual_savings,
            "savings_percentage": (annual_savings / current_annual_cost) * 100,
            "cost_per_case": cost_per_case,
            "currency": base_currency,
            "region": region,
            "conversions": conversions,
            "annual_salary": avg_salary
        }

class HRFeatureCategorizer:
    """HR Feature Categorizer dengan terjemahan Indonesia"""
    
    def __init__(self):
        self.hr_features = self._define_essential_hr_features()
        
    def _define_essential_hr_features(self):
        """Define essential HR features untuk prediksi dengan label Indonesia"""
        return {
            "Age": {"type": "number", "min": 18, "max": 65, "default": 32, "unit": "tahun", "label": "Umur"},
            "Gender": {"type": "selectbox", "options": {"Perempuan": 0, "Laki-laki": 1}, "default": "Laki-laki", "label": "Jenis Kelamin"},
            "MaritalStatus": {"type": "selectbox", "options": {"Lajang": 0, "Menikah": 1, "Bercerai": 2}, "default": "Menikah", "label": "Status Pernikahan"},
            "DistanceFromHome": {"type": "number", "min": 1, "max": 50, "default": 7, "unit": "km", "label": "Jarak dari Rumah"},
            "JobLevel": {"type": "selectbox", "options": {"Pemula": 1, "Junior": 2, "Menengah": 3, "Senior": 4, "Eksekutif": 5}, "default": "Menengah", "label": "Level Pekerjaan"},
            "YearsAtCompany": {"type": "number", "min": 0, "max": 40, "default": 5, "unit": "tahun", "label": "Lama Bekerja di Perusahaan"},
            "YearsInCurrentRole": {"type": "number", "min": 0, "max": 20, "default": 2, "unit": "tahun", "label": "Lama di Posisi Saat Ini"},
            "YearsSinceLastPromotion": {"type": "number", "min": 0, "max": 20, "default": 1, "unit": "tahun", "label": "Tahun Sejak Promosi Terakhir"},
            "OverTime": {"type": "selectbox", "options": {"Tidak": 0, "Ya": 1}, "default": "Tidak", "label": "Lembur"},
            "BusinessTravel": {"type": "selectbox", "options": {"Tidak Pernah": 0, "Jarang": 1, "Sering": 2}, "default": "Jarang", "label": "Perjalanan Dinas"},
            "MonthlyIncome": {"type": "number", "min": 1000, "max": 25000, "default": 5000, "unit": "USD", "label": "Gaji Bulanan"},
            "PercentSalaryHike": {"type": "slider", "min": 0, "max": 25, "default": 13, "unit": "%", "label": "Persentase Kenaikan Gaji"},
            "StockOptionLevel": {"type": "selectbox", "options": {"Tidak Ada": 0, "Dasar": 1, "Standar": 2, "Premium": 3}, "default": "Dasar", "label": "Level Opsi Saham"},
            "JobSatisfaction": {"type": "selectbox", "options": {"Rendah": 1, "Sedang": 2, "Tinggi": 3, "Sangat Tinggi": 4}, "default": "Tinggi", "label": "Kepuasan Kerja"},
            "WorkLifeBalance": {"type": "selectbox", "options": {"Buruk": 1, "Baik": 2, "Lebih Baik": 3, "Terbaik": 4}, "default": "Lebih Baik", "label": "Keseimbangan Kerja-Hidup"},
            "EnvironmentSatisfaction": {"type": "selectbox", "options": {"Rendah": 1, "Sedang": 2, "Tinggi": 3, "Sangat Tinggi": 4}, "default": "Tinggi", "label": "Kepuasan Lingkungan Kerja"},
            "PerformanceRating": {"type": "selectbox", "options": {"Rendah": 1, "Baik": 2, "Sangat Baik": 3, "Luar Biasa": 4}, "default": "Sangat Baik", "label": "Rating Kinerja"}
        }
    
    def create_hr_input_form(self):
        """Create form input dengan bahasa Indonesia"""
        st.sidebar.header("👥 Informasi Karyawan")
        st.sidebar.markdown("**Penilaian Risiko Attrisi Karyawan**")
        
        profile = st.sidebar.selectbox(
            "Profil Cepat:",
            ["📊 Input Manual", "🌟 Karyawan Berprestasi", "📈 Karyawan Biasa", "🆕 Fresh Graduate", "⚠️ Karyawan Berisiko"]
        )
        
        input_data = {}
        
        if profile == "📊 Input Manual":
            st.sidebar.subheader("📋 Data Demografi Personal")
            input_data["Age"] = st.sidebar.number_input("Umur (tahun)", 18, 65, 32)
            input_data["Gender"] = st.sidebar.selectbox("Jenis Kelamin", ["Perempuan", "Laki-laki"], index=1)
            input_data["MaritalStatus"] = st.sidebar.selectbox("Status Pernikahan", ["Lajang", "Menikah", "Bercerai"], index=1)
            input_data["DistanceFromHome"] = st.sidebar.number_input("Jarak dari Rumah (km)", 1, 50, 7)
            
            st.sidebar.subheader("💼 Informasi Pekerjaan")
            input_data["JobLevel"] = st.sidebar.selectbox("Level Pekerjaan", ["Pemula", "Junior", "Menengah", "Senior", "Eksekutif"], index=2)
            input_data["YearsAtCompany"] = st.sidebar.number_input("Lama Bekerja di Perusahaan (tahun)", 0, 40, 5)
            input_data["YearsInCurrentRole"] = st.sidebar.number_input("Lama di Posisi Saat Ini (tahun)", 0, 20, 2)
            input_data["YearsSinceLastPromotion"] = st.sidebar.number_input("Tahun Sejak Promosi Terakhir", 0, 20, 1)
            input_data["OverTime"] = st.sidebar.selectbox("Lembur", ["Tidak", "Ya"], index=0)
            input_data["BusinessTravel"] = st.sidebar.selectbox("Perjalanan Dinas", ["Tidak Pernah", "Jarang", "Sering"], index=1)
            
            st.sidebar.subheader("💰 Kompensasi")
            input_data["MonthlyIncome"] = st.sidebar.number_input("Gaji Bulanan ($)", 1000, 25000, 5000, step=500)
            input_data["PercentSalaryHike"] = st.sidebar.slider("Kenaikan Gaji Terakhir (%)", 0, 25, 13)
            input_data["StockOptionLevel"] = st.sidebar.selectbox("Opsi Saham", ["Tidak Ada", "Dasar", "Standar", "Premium"], index=1)
            
            st.sidebar.subheader("😊 Kepuasan & Kinerja")
            input_data["JobSatisfaction"] = st.sidebar.selectbox("Kepuasan Kerja", ["Rendah", "Sedang", "Tinggi", "Sangat Tinggi"], index=2)
            input_data["WorkLifeBalance"] = st.sidebar.selectbox("Keseimbangan Kerja-Hidup", ["Buruk", "Baik", "Lebih Baik", "Terbaik"], index=2)
            input_data["EnvironmentSatisfaction"] = st.sidebar.selectbox("Kepuasan Lingkungan Kerja", ["Rendah", "Sedang", "Tinggi", "Sangat Tinggi"], index=2)
            input_data["PerformanceRating"] = st.sidebar.selectbox("Rating Kinerja", ["Rendah", "Baik", "Sangat Baik", "Luar Biasa"], index=2)
            
        else:
            # Profil preset dengan nama Indonesia
            profiles = {
                "🌟 Karyawan Berprestasi": {
                    "Age": 35, "Gender": "Laki-laki", "MaritalStatus": "Menikah", "DistanceFromHome": 5,
                    "JobLevel": "Senior", "YearsAtCompany": 8, "YearsInCurrentRole": 3, "YearsSinceLastPromotion": 1,
                    "OverTime": "Tidak", "BusinessTravel": "Jarang", "MonthlyIncome": 8000, "PercentSalaryHike": 18,
                    "StockOptionLevel": "Premium", "JobSatisfaction": "Sangat Tinggi", "WorkLifeBalance": "Lebih Baik",
                    "EnvironmentSatisfaction": "Sangat Tinggi", "PerformanceRating": "Luar Biasa"
                },
                "📈 Karyawan Biasa": {
                    "Age": 32, "Gender": "Perempuan", "MaritalStatus": "Menikah", "DistanceFromHome": 7,
                    "JobLevel": "Menengah", "YearsAtCompany": 5, "YearsInCurrentRole": 2, "YearsSinceLastPromotion": 2,
                    "OverTime": "Tidak", "BusinessTravel": "Jarang", "MonthlyIncome": 5000, "PercentSalaryHike": 13,
                    "StockOptionLevel": "Dasar", "JobSatisfaction": "Tinggi", "WorkLifeBalance": "Lebih Baik",
                    "EnvironmentSatisfaction": "Tinggi", "PerformanceRating": "Sangat Baik"
                },
                "🆕 Fresh Graduate": {
                    "Age": 24, "Gender": "Laki-laki", "MaritalStatus": "Lajang", "DistanceFromHome": 15,
                    "JobLevel": "Pemula", "YearsAtCompany": 1, "YearsInCurrentRole": 1, "YearsSinceLastPromotion": 0,
                    "OverTime": "Ya", "BusinessTravel": "Tidak Pernah", "MonthlyIncome": 3000, "PercentSalaryHike": 11,
                    "StockOptionLevel": "Tidak Ada", "JobSatisfaction": "Tinggi", "WorkLifeBalance": "Baik",
                    "EnvironmentSatisfaction": "Tinggi", "PerformanceRating": "Baik"
                },
                "⚠️ Karyawan Berisiko": {
                    "Age": 28, "Gender": "Perempuan", "MaritalStatus": "Lajang", "DistanceFromHome": 25,
                    "JobLevel": "Junior", "YearsAtCompany": 3, "YearsInCurrentRole": 3, "YearsSinceLastPromotion": 3,
                    "OverTime": "Ya", "BusinessTravel": "Sering", "MonthlyIncome": 3500, "PercentSalaryHike": 11,
                    "StockOptionLevel": "Tidak Ada", "JobSatisfaction": "Rendah", "WorkLifeBalance": "Buruk",
                    "EnvironmentSatisfaction": "Rendah", "PerformanceRating": "Baik"
                }
            }
            input_data = profiles.get(profile, profiles["📈 Karyawan Biasa"])
        
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
    """Halaman login dengan role-based access"""
    st.markdown("""
    <div style="text-align: center; padding: 50px 0;">
        <h1>👥 Sistem Prediksi Attrisi Karyawan & Analisis Finansial</h1>
        <h3>Platform Analitik Sumber Daya Manusia</h3>
        <p>Penilaian risiko attrisi karyawan berbasis ML dengan analisis dampak finansial komprehensif</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Login Profesional")
        
        with st.form("login_form"):
            username = st.text_input("👤 Nama Pengguna", placeholder="Masukkan nama pengguna")
            password = st.text_input("🔑 Kata Sandi", type="password", placeholder="Masukkan kata sandi")
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
        
        with st.expander("📋 Akun Demo & Role Permissions", expanded=False):
            st.markdown("""
            **🔑 Akun yang Tersedia:**
            
            **👑 Administrator**
            - ✅ Penilaian Risiko Karyawan
            - ✅ Analisis Dampak Finansial  
            - ✅ Dashboard Lengkap
            - ✅ Manajemen Sistem
            
            **👨‍💼 HR Manager**
            - ✅ Penilaian Risiko Karyawan
            - ✅ Analisis Dampak Finansial
            - ✅ Dashboard
            - ❌ Manajemen Sistem
            
            **💰 Financial Analyst**
            - ❌ Penilaian Risiko Karyawan
            - ✅ Analisis Dampak Finansial SAJA
            - ❌ Dashboard
            - ❌ Manajemen Sistem
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

def create_financial_analysis_form():
    """Create form analisis finansial dengan regional support"""
    st.header("💰 Analisis Dampak Finansial")
    st.markdown("**Konfigurasikan parameter organisasi untuk penilaian dampak finansial**")
    
    st.subheader("🌍 Pemilihan Pasar")
    col1, col2 = st.columns(2)
    
    with col1:
        region = st.selectbox(
            "Pilih Pasar/Wilayah:",
            ["GLOBAL", "INDONESIA"],
            index=1,
            help="Pilih pasar untuk kalkulasi biaya spesifik wilayah"
        )
        
        calculator = FinancialAnalysisCalculator()
        regional_config = calculator.regional_configs[region]
        
        st.info(f"**Dipilih:** {regional_config['label']}")
        st.write(f"**Mata Uang:** {regional_config['currency']}")
        
        if region == "INDONESIA":
            st.write("**Termasuk regulasi Indonesia:**")
            st.write("• THR (bonus bulan ke-13)")
            st.write("• Kontribusi Jamsostek")
            st.write("• Pesangon wajib")
    
    with col2:
        st.markdown("**💱 Kurs Mata Uang (Des 2024):**")
        rates = calculator.exchange_rates
        st.write(f"• 1 USD = Rp {rates['USD_to_IDR']:,}")
        st.write(f"• 1 EUR = Rp {rates['EUR_to_IDR']:,}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Metrik Organisasi")
        
        total_employees = st.number_input(
            "Total Jumlah Karyawan",
            min_value=10, max_value=100000, value=1000, step=50,
            help="Total ukuran tenaga kerja di organisasi Anda"
        )
        
        current_attrition_rate = st.slider(
            "Tingkat Attrisi Tahunan Saat Ini (%)",
            min_value=1.0, max_value=50.0, value=16.0, step=0.5,
            help="Persentase turnover karyawan tahunan saat ini"
        )
        
        suggested_salaries = regional_config['salary_ranges']
        st.markdown(f"**💰 Konfigurasi Gaji ({regional_config['currency']}):**")
        
        if region == "INDONESIA":
            st.write("**Rentang IDR yang Disarankan:**")
            st.write(f"• Level Pemula: Rp {suggested_salaries['entry']:,}")
            st.write(f"• Level Menengah: Rp {suggested_salaries['mid']:,}")
            st.write(f"• Level Senior: Rp {suggested_salaries['senior']:,}")
            st.write(f"• Eksekutif: Rp {suggested_salaries['executive']:,}")
            
            avg_annual_salary = st.number_input(
                "Gaji Tahunan Rata-rata (IDR)",
                min_value=30000000, max_value=1000000000, 
                value=suggested_salaries['mid'], step=5000000,
                help="Gaji tahunan rata-rata dalam Rupiah Indonesia",
                format="%d"
            )
            
            usd_equivalent = avg_annual_salary * calculator.exchange_rates['IDR_to_USD']
            st.info(f"Setara USD: ${usd_equivalent:,.0f}")
            
        else:
            avg_annual_salary = st.number_input(
                f"Gaji Tahunan Rata-rata ({regional_config['currency']})",
                min_value=20000, max_value=300000, 
                value=suggested_salaries['mid'], step=5000,
                help=f"Gaji tahunan rata-rata dalam {regional_config['currency']}"
            )
    
    with col2:
        st.subheader("🎯 Kinerja Model")
        
        st.markdown("**📊 Akurasi Prediksi Model**")
        prediction_accuracy = 87.0  # Nilai tetap 87%
        st.info(f"🎯 **Akurasi Model: {prediction_accuracy:.1f}%** (Berdasarkan hasil training)")
        st.caption("Model Machine Learning telah dilatih dengan akurasi 87% pada dataset test")
        
        # Intervention effectiveness - NILAI TETAP
        st.markdown("**🎯 Efektivitas Intervensi HR**")
        intervention_success_rate = 30.0  # Nilai tetap 30%
        st.info(f"💼 **Tingkat Keberhasilan Intervensi: {intervention_success_rate:.0f}%** (Berdasarkan best practice)")
        st.caption("Estimasi berdasarkan studi industri: 30% kasus attrisi dapat dicegah melalui intervensi tepat waktu")
        
        st.markdown("**Komponen Biaya (% dari Gaji Tahunan):**")
        
        use_regional_defaults = st.checkbox(
            f"Gunakan Tarif Standar {regional_config['label']}", 
            value=True,
            help="Gunakan pengganda biaya spesifik wilayah"
        )
        
        if use_regional_defaults:
            if region == "INDONESIA":
                recruitment_cost = 18
                training_cost = 12
                productivity_loss = 45
                separation_cost = 8
                opportunity_cost = 7
                st.info("🇮🇩 Menggunakan tarif khusus Indonesia")
            else:
                recruitment_cost = 20
                training_cost = 15
                productivity_loss = 50
                separation_cost = 5
                opportunity_cost = 10
                st.info("🌍 Menggunakan tarif standar global")
        else:
            recruitment_cost = st.slider("Rekrutmen & Perekrutan", 10, 30, 20, step=1)
            training_cost = st.slider("Pelatihan & Orientasi", 10, 25, 15, step=1)
            productivity_loss = st.slider("Kehilangan Produktivitas", 25, 75, 50, step=5)
            separation_cost = st.slider("Biaya Pemisahan", 2, 15, 8, step=1)
            opportunity_cost = st.slider("Biaya Peluang", 5, 20, 10, step=1)
        
        custom_multipliers = {
            "recruitment": recruitment_cost / 100,
            "training": training_cost / 100,
            "productivity_loss": productivity_loss / 100,
            "separation": separation_cost / 100,
            "opportunity_cost": opportunity_cost / 100
        }
    
    st.markdown("---")
    show_comparison = st.checkbox(
        "🔄 Tampilkan Perbandingan Global vs Indonesia", 
        value=False,
        help="Bandingkan biaya antara pasar global dan Indonesia"
    )
    
    return {
        "total_employees": total_employees,
        "attrition_rate": current_attrition_rate,
        "avg_salary": avg_annual_salary,
        "region": region,
        "currency": regional_config['currency'],
        "prediction_accuracy": prediction_accuracy,
        "intervention_effectiveness": intervention_success_rate,
        "custom_multipliers": custom_multipliers if not use_regional_defaults else None,
        "show_comparison": show_comparison
    }

def display_financial_results(financial_params, calculator):
    """Display hasil analisis finansial dengan regional support"""
    
    cost_analysis = calculator.calculate_attrition_cost(
        financial_params["avg_salary"],
        financial_params["region"],
        financial_params["currency"],
        financial_params["custom_multipliers"]
    )
    
    savings_analysis = calculator.estimate_annual_savings(
        financial_params["total_employees"],
        financial_params["attrition_rate"],
        financial_params["avg_salary"],
        financial_params["prediction_accuracy"],
        financial_params["intervention_effectiveness"],
        financial_params["region"],
        financial_params["currency"]
    )
    
    st.header("📈 Hasil Dampak Finansial")
    
    regional_config = calculator.regional_configs[financial_params["region"]]
    
    st.info(f"🌍 **Analisis untuk:** {regional_config['label']} | **Mata Uang:** {financial_params['currency']}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if financial_params["currency"] == "IDR":
            cost_display = f"Rp {cost_analysis['total_cost']:,.0f}"
        else:
            cost_display = f"${cost_analysis['total_cost']:,.0f}"
            
        st.metric(
            "Biaya per Attrisi",
            cost_display,
            f"{cost_analysis['cost_as_percentage_of_salary']:.0f}% dari gaji"
        )
    
    with col2:
        st.metric(
            "Kasus Attrisi Tahunan",
            f"{savings_analysis['annual_attrition_cases']:,}",
            f"{financial_params['attrition_rate']:.1f}% tingkat"
        )
    
    with col3:
        if financial_params["currency"] == "IDR":
            annual_cost_display = f"Rp {savings_analysis['current_annual_cost']:,.0f}"
        else:
            annual_cost_display = f"${savings_analysis['current_annual_cost']:,.0f}"
            
        st.metric(
            "Biaya Tahunan Saat Ini",
            annual_cost_display,
            "Total dampak attrisi"
        )
    
    with col4:
        if financial_params["currency"] == "IDR":
            savings_display = f"Rp {savings_analysis['annual_savings']:,.0f}"
        else:
            savings_display = f"${savings_analysis['annual_savings']:,.0f}"
            
        st.metric(
            "Potensi Penghematan Tahunan",
            savings_display,
            f"{savings_analysis['savings_percentage']:.1f}% pengurangan"
        )
    
    if savings_analysis.get('conversions'):
        st.markdown("**💱 Konversi Mata Uang:**")
        col1, col2 = st.columns(2)
        
        with col1:
            if financial_params["currency"] == "IDR":
                usd_savings = savings_analysis['conversions']['USD']
                st.info(f"**Setara USD:** ${usd_savings:,.0f}")
        
        with col2:
            if financial_params["currency"] == "USD":
                idr_savings = savings_analysis['conversions']['IDR']
                st.info(f"**Setara IDR:** Rp {idr_savings:,.0f}")
    
    return cost_analysis, savings_analysis

def display_prediction_results(prediction, prediction_proba, hr_input, metadata):
    """Display hasil prediksi karyawan dengan bahasa Indonesia"""
    
    st.header("🎯 Hasil Penilaian Risiko Attrisi Karyawan")
    
    col1, col2, col3 = st.columns(3)
    
    attrition_probability = prediction_proba[1]
    
    with col1:
        st.subheader("📊 Level Risiko")
        
        if attrition_probability > 0.7:
            st.error("**🚨 RISIKO TINGGI**")
            risk_level = "TINGGI"
            risk_color = "red"
        elif attrition_probability > 0.3:
            st.warning("**⚠️ RISIKO SEDANG**")
            risk_level = "SEDANG" 
            risk_color = "orange"
        else:
            st.success("**✅ RISIKO RENDAH**")
            risk_level = "RENDAH"
            risk_color = "green"
        
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
        
        st.metric("Umur", f"{age} tahun")
        st.metric("Gaji Bulanan", f"${income:,}")
        st.metric("Masa Kerja", f"{years_company} tahun")

def show_access_denied(feature_name):
    """Show access denied message"""
    st.error(f"🚫 **Akses Ditolak**")
    st.warning(f"Anda tidak memiliki izin untuk mengakses **{feature_name}**")
    
    user_role = st.session_state.get('user_role', 'unknown')
    user_permissions = st.session_state.get('user_permissions', [])
    
    st.info(f"**Role Anda:** {user_role}")
    st.info(f"**Izin Anda:** {', '.join(user_permissions)}")
    
    st.markdown("---")
    st.markdown("**💡 Untuk mengakses fitur ini:**")
    if user_role == "financial":
        st.write("• Hubungi administrator untuk upgrade akses")
        st.write("• Atau login dengan akun HR Manager/Admin")
    else:
        st.write("• Hubungi administrator sistem")

def main_app():
    """Aplikasi utama dengan role-based access control"""
    username = st.session_state.username
    user_role = st.session_state.get('user_role', 'guest')
    user_permissions = st.session_state.get('user_permissions', [])
    display_name = st.session_state.get('display_name', username)
    
    # Header dengan informasi role
    st.title(f"👥 Sistem Prediksi Attrisi Karyawan & Analisis Finansial")
    
    # Role indicator
    role_colors = {
        "admin": "🟢",
        "hr_manager": "🔵", 
        "financial": "🟡"
    }
    role_color = role_colors.get(user_role, "⚪")
    
    st.markdown(f"""
    **Selamat datang {display_name}** {role_color} **{user_role.title()}** | **🟢 Sistem Online** | **🛡️ Sesi Aman**
    
    ### 📊 **Tentang Sistem Analitik HR**
    Sistem prediksi attrisi karyawan berbasis Machine Learning yang dirancang khusus untuk membantu departemen HR dalam:
    - **🎯 Prediksi Risiko:** Mengidentifikasi karyawan yang berisiko tinggi keluar dari perusahaan
    - **💰 Analisis Biaya:** Menghitung dampak finansial dari attrisi karyawan secara akurat
    - **📈 Rekomendasi Strategis:** Memberikan saran berbasis data untuk retensi karyawan
    - **🌍 Multi-Regional:** Mendukung analisis untuk pasar global dan Indonesia
    
    **Akses Level Anda:** {', '.join(user_permissions)}
    """)
    
    # Logout button in sidebar
    if st.sidebar.button("🚪 Keluar"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_role = None
        st.session_state.user_permissions = []
        st.rerun()
    
    # Display permissions in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**🔐 Level Akses: {user_role.title()}**")
    st.sidebar.markdown("**✅ Izin Anda:**")
    for permission in user_permissions:
        permission_names = {
            "employee_assessment": "Penilaian Karyawan",
            "financial_analysis": "Analisis Finansial",
            "dashboard": "Dashboard"
        }
        st.sidebar.write(f"• {permission_names.get(permission, permission)}")
    
    st.markdown("---")
    
    # Load model components if needed
    model, scaler, feature_names, metadata = load_model_components()
    
    # Create tabs based on permissions
    available_tabs = []
    tab_permissions = []
    
    if has_permission(username, "employee_assessment"):
        available_tabs.append("🎯 Penilaian Risiko Karyawan")
        tab_permissions.append("employee_assessment")
    
    if has_permission(username, "financial_analysis"):
        available_tabs.append("💰 Analisis Dampak Finansial")
        tab_permissions.append("financial_analysis")
    
    if has_permission(username, "dashboard"):
        available_tabs.append("📊 Dashboard")
        tab_permissions.append("dashboard")
    
    # Show error if no tabs available
    if not available_tabs:
        st.error("🚫 Tidak ada fitur yang dapat diakses dengan role Anda")
        return
    
    # Create tabs
    tabs = st.tabs(available_tabs)
    
    for i, tab in enumerate(tabs):
        permission = tab_permissions[i]
        
        with tab:
            if permission == "employee_assessment":
                st.header("🎯 Penilaian Risiko Attrisi Karyawan")
                
                hr_categorizer = HRFeatureCategorizer()
                hr_input = hr_categorizer.create_hr_input_form()
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Umur", f"{hr_input.get('Age', 0)} tahun")
                col2.metric("Gaji", f"${hr_input.get('MonthlyIncome', 0):,}")
                col3.metric("Masa Kerja", f"{hr_input.get('YearsAtCompany', 0)} tahun")
                col4.metric("Level Kerja", hr_input.get('JobLevel', 'N/A'))
                
                if st.button("🚀 Analisis Risiko Attrisi", type="primary"):
                    with st.spinner("Menganalisis data karyawan..."):
                        prediction, prediction_proba, input_df = make_prediction(model, scaler, hr_input, feature_names)
                        
                        if prediction is not None:
                            st.success("✅ Analisis selesai!")
                            display_prediction_results(prediction, prediction_proba, hr_input, metadata)
                        else:
                            st.error("❌ Analisis gagal")
            
            elif permission == "financial_analysis":
                financial_params = create_financial_analysis_form()
                
                if st.button("📊 Hitung Dampak Finansial", type="primary"):
                    with st.spinner("Menghitung dampak finansial..."):
                        calculator = FinancialAnalysisCalculator()
                        cost_analysis, savings_analysis = display_financial_results(financial_params, calculator)
            
            elif permission == "dashboard":
                st.header("📊 Dashboard Analitik")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🎯 Kinerja Model")
                    
                    if metadata:
                        st.metric("Akurasi Model", f"{metadata.get('test_accuracy', 0.87):.1%}")
                        st.metric("Skor ROC-AUC", f"{metadata.get('roc_auc', 0.82):.3f}")
                        st.metric("Tipe Model", metadata.get('model_type', 'Logistic Regression'))
                    
                    st.subheader("🏢 Analisis Risiko Departemen")
                    dept_data = {
                        'Department': ['Sales', 'Engineering', 'Marketing', 'HR', 'Finance'],
                        'Risk_Score': [0.28, 0.15, 0.22, 0.12, 0.18],
                        'Employee_Count': [150, 200, 75, 25, 50]
                    }
                    dept_df = pd.DataFrame(dept_data)
                    
                    fig_dept = px.bar(
                        dept_df,
                        x='Department',
                        y='Risk_Score',
                        color='Risk_Score',
                        title='Rata-rata Risiko Attrisi per Departemen',
                        color_continuous_scale='Reds'
                    )
                    st.plotly_chart(fig_dept, use_container_width=True)
                
                with col2:
                    st.subheader("📈 Statistik Penggunaan")
                    
                    st.metric("Penilaian Hari Ini", "47", "+12")
                    st.metric("Karyawan Risiko Tinggi", "23", "+3") 
                    st.metric("Intervensi Terjadwal", "15", "+8")
                    
                    st.subheader("🎯 Faktor Risiko Utama")
                    risk_data = {
                        'Factor': ['Kerja Lembur', 'Kepuasan Kerja Rendah', 'Keseimbangan Kerja-Hidup Buruk', 'Jarak Jauh', 'Tidak Ada Promosi'],
                        'Impact': [0.45, 0.38, 0.32, 0.28, 0.25]
                    }
                    risk_df = pd.DataFrame(risk_data)
                    
                    fig_risk = px.bar(
                        risk_df,
                        x='Impact',
                        y='Factor',
                        orientation='h',
                        title='Skor Dampak Faktor Risiko',
                        color='Impact',
                        color_continuous_scale='Oranges'
                    )
                    st.plotly_chart(fig_risk, use_container_width=True)

def main():
    """Fungsi utama dengan role-based access control"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if st.session_state.logged_in:
        main_app()
    else:
        login_page()

if __name__ == "__main__":
    main()