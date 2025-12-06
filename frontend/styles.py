def get_app_css():
    return """
    <style>
        /* --- 1. DEFINICIÓN DE VARIABLES GLOBALES (Tema Corporativo) --- */
        :root {
            --primary-color: #0F2942;    /* Navy Blue Profundo */
            --secondary-color: #F1F5F9;  /* Slate-50 (Fondo General) */
            --sidebar-bg: #1E293B;       /* Slate-800 (Fondo Sidebar) */
            --text-color: #334155;       /* Slate-700 (Texto Principal) */
            --text-light: #94A3B8;       /* Slate-400 (Texto Secundario) */
            --white: #FFFFFF;
            --success: #10B981;          /* Emerald-500 */
            --danger: #EF4444;           /* Red-500 */
            
            /* Sombras Suaves (Efecto Elevación) */
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            
            --font-family: 'Inter', 'Roboto', 'Helvetica Neue', sans-serif;
        }

        /* --- 2. RESET Y TIPOGRAFÍA BASE --- */
        html, body, [class*="css"] {
            font-family: var(--font-family);
            color: var(--text-color);
            -webkit-font-smoothing: antialiased; /* Texto más nítido en Mac/iOS */
        }
        
        /* Fondo de la aplicación principal */
        .stApp {
            background-color: var(--secondary-color);
        }

        /* --- 3. LIMPIEZA DE INTERFAZ (Streamlit Hacking) --- */
        /* Ocultar menú hamburguesa, footer y barra superior de colores */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        [data-testid="stDecoration"] {display: none;}
        
        /* Eliminar padding excesivo superior */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }

        /* --- 4. SIDEBAR PERSONALIZADO --- */
        [data-testid="stSidebar"] {
            background-color: var(--sidebar-bg);
            border-right: 1px solid #334155;
        }
        
        /* Textos en Sidebar */
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #F8FAFC !important; /* Blanco */
        }
        
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div {
            color: var(--text-light) !important;
        }
        
        /* Separadores en Sidebar */
        [data-testid="stSidebar"] hr {
            border-color: #475569 !important;
        }

        /* --- 5. COMPONENTE: TARJETA DE LOGIN (Clases Custom) --- */
        .login-container {
            max-width: 420px;
            margin: 8vh auto; /* Centrado vertical y horizontal */
            padding: 40px;
            background-color: var(--white);
            border-radius: 16px;
            box-shadow: var(--shadow-lg);
            text-align: center;
            border-top: 6px solid var(--primary-color); /* Acento de marca superior */
        }
        
        .login-header {
            font-size: 26px;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 8px;
        }
        
        .login-subtext {
            font-size: 14px;
            color: #64748B;
            margin-bottom: 32px;
        }

        /* --- 6. COMPONENTE: TARJETAS DE MÉTRICAS (KPIs) --- */
        /* Usaremos st.markdown con estas clases para reemplazar st.metric plano */
        .metric-card {
            background-color: var(--white);
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 24px;
            box-shadow: var(--shadow-sm);
            transition: all 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-md);
            border-color: #CBD5E1;
        }
        
        .metric-title {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748B;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary-color);
        }

        /* --- 7. ESTILIZACIÓN DE BOTONES --- */
        /* Botón Primario */
        .stButton > button {
            background-color: var(--primary-color) !important;
            color: white !important;
            border: none;
            border-radius: 8px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            transition: background-color 0.2s, transform 0.1s;
            box-shadow: var(--shadow-sm);
        }
        
        .stButton > button:hover {
            background-color: #173856 !important; /* Un poco más claro/oscuro al hover */
            box-shadow: var(--shadow-md);
            transform: translateY(-1px);
        }
        
        .stButton > button:active {
            transform: translateY(0);
        }

        /* --- 8. ESTILIZACIÓN DE TABLAS (DataFrames) --- */
        [data-testid="stDataFrame"] {
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: var(--shadow-sm);
            background-color: var(--white);
        }
        
        /* Cabecera de Tabla */
        [data-testid="stDataFrame"] thead th {
            background-color: #F8FAFC !important;
            color: var(--primary-color) !important;
            font-weight: 600 !important;
            border-bottom: 2px solid #E2E8F0 !important;
        }

        /* --- 9. ALERTAS Y NOTIFICACIONES --- */
        .stAlert {
            border-radius: 8px;
            box-shadow: var(--shadow-sm);
            border: none;
        }

        /* --- NUEVO: Estilización de Inputs Generales (Text, Date) --- */
        /* Targets st.text_input, st.date_input, st.number_input, etc. */
        [data-testid="stTextInput"] > div > div > input,
        [data-testid="stDateInput"] > div > div > input {
            /* Estilo Base del Campo */
            border: 1px solid #CBD5E1; /* Gris claro (Steel) */
            background-color: #F8FAFC; /* Fondo muy suave para diferenciar */
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 1rem;
            color: var(--text-color);
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        /* Efecto de Foco (cuando el campo está seleccionado) */
        [data-testid="stTextInput"] > div > div > input:focus,
        [data-testid="stDateInput"] > div > div > input:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 1px var(--primary-color);
            outline: none;
        }

        /* Estilo del Placeholder (el texto "Ej. SKU-..." ) */
        [data-testid="stTextInput"] > div > div > input::placeholder {
            color: #94A3B8; /* Gris tenue */
            font-style: italic;
        }
        
    </style>
    """