# Predictive System for Automotive Inventory Management

## 1. Introduction

This project presents a predictive system designed to address inventory management challenges within the automotive parts sector. Developed as part of a university thesis, this application leverages Machine Learning (ML) techniques to forecast product demand at the Stock Keeping Unit (SKU) level, aiming to optimize inventory levels and mitigate issues like stockouts and overstocking.

The system replaces traditional manual forecasting methods, often based on aggregated financial reports, with a data-driven approach using historical transactional sales data.

**Target Audiences:**
* **Technical Leaders / Hiring Managers:** Showcases a full-stack application integrating data processing, ML modeling, API development, and a web-based UI. Demonstrates proficiency in Python, common data science libraries, web frameworks, and database interaction.
* **Thesis Jury / Reviewers:** Details the practical implementation of the thesis proposal, demonstrating how ML can solve the identified problem of inefficient inventory management by predicting SKU-level demand based on historical sales transactions.

## 2. Problem Statement

The core problem addressed is **inefficient inventory management** common in the automotive parts industry. Traditional methods often rely on manual analysis of aggregated financial summaries (e.g., quarterly sales per category). This high-level view makes it difficult to predict the demand for specific SKUs accurately, leading to:
* **Stockouts:** Missing sales opportunities for popular items.
* **Overstocking:** Tying up capital in slow-moving inventory.

This project aims to replace this inefficient manual process with an automated, data-driven prediction system.

## 3. Proposed Solution

The software implements an end-to-end ML pipeline:

1.  **Data Ingestion:** Allows users to upload historical sales data, either as pre-processed CSV files or directly using the company's Excel reports (`Factura_Importacion_PLUS_*.xlsx`), automatically extracting relevant transactional details from the 'Detalle' sheet.
2.  **Data Storage:** Cleans and stores the transactional data (SKU, Date, Quantity Sold) in a structured PostgreSQL database (`ventas_detalle` table).
3.  **ML Pipeline:**
    * **Preprocessing (`preprocessing.py`):** Reads data from the database, performs cleaning, generates date-based features (month, day, day of week, year), encodes categorical features (`id_producto`/SKU using `LabelEncoder`), and scales numerical features (`MinMaxScaler`).
    * **Training (`training.py`):** Trains two regression models (XGBoost and a Multi-Layer Perceptron - MLP using TensorFlow/Keras) to predict `cantidad_vendida` (quantity sold) based on the preprocessed features. Saves the trained models and transformers (encoder, scaler) as artifacts in the `models/` directory.
4.  **Prediction API (`routes.py`):** Provides a Flask-based REST API endpoint (`/predict`) that accepts an SKU and a future date.
5.  **Prediction Logic (`predict.py`):** This core module loads the saved artifacts (encoder, scaler, MLP model) once at startup. When called by the API, it replicates the *exact same* preprocessing steps (feature engineering, encoding, scaling) on the input SKU/date and then uses the loaded MLP model to generate the demand prediction (in units).
6.  **Web Interface (Streamlit):** Provides a user-friendly interface (`1_Carga_de_Datos.py`, `2_Visualizacion_de_Prediccion.py`) for:
    * Uploading historical data.
    * Requesting demand predictions for specific SKUs and dates.
    * Visualizing the prediction alongside the product's historical sales data (obtained via the `/history` API endpoint).

## 4. Technology Stack

* **Backend:** Python 3.12+, Flask, Flask-CORS
* **Frontend:** Streamlit
* **Machine Learning:** Scikit-learn (`LabelEncoder`, `MinMaxScaler`, `train_test_split`), TensorFlow (Keras for MLP), XGBoost
* **Data Handling:** Pandas, NumPy
* **Database:** PostgreSQL, SQLAlchemy, pg8000
* **Serialization:** Joblib (for Scikit-learn objects)
* **Excel Reading:** openpyxl

## 5. Project Structure

```text
./
├── backend/
│   ├── api/
│   │   └── routes.py       # Flask API endpoints (/upload, /predict, /history)
│   ├── database/
│   │   └── db_utils.py     # Database connection and CRUD operations
│   ├── ml_core/
│   │   ├── predict.py      # Prediction logic (loads artifacts, preprocesses input, predicts)
│   │   ├── preprocessing.py# Data cleaning, feature engineering, encoding, scaling
│   │   └── training.py     # Model training (XGBoost, MLP) and evaluation pipeline
│   ├── app.py              # Flask application factory and entry point
│   └── config.py           # Database URI configuration (should be gitignored or managed securely)
├── frontend/
│   ├── pages/
│   │   ├── 1_Carga_de_Datos.py # Streamlit page for data upload
│   │   └── 2_Visualizacion_de_Prediccion.py # Streamlit page for prediction request/display
│   └── Inicio.py           # Streamlit main/home page
├── models/                 # Stores saved ML artifacts (.joblib, .keras) - Gitignored recommended
├── docs/
│   └── Explicacion_Prediccion_MVP.md # Detailed explanation of the prediction flow
├── venv/                   # Virtual environment (Gitignored)
├── .gitignore
├── requirements.txt        # Project dependencies
└── README.md               # This file
```

## 6. Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd Python_Predictive_system_for_automotive_company
    ```
2.  **Create and Activate Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  4.  **Setup PostgreSQL Database:**
    * Ensure you have a PostgreSQL server installed and running (v16 recommended).
    * Create a dedicated user and database:
        ```sql
        CREATE USER teo_user WITH PASSWORD 'teo_password_segura';
        CREATE DATABASE teo_db OWNER teo_user;
        ```
    * Configure the database connection string in `backend/config.py` using the `pg8000` driver:
      `DATABASE_URI = "postgresql+pg8000://teo_user:teo_password_segura@localhost:5432/teo_db"`
    * **Important:** Use environment variables for credentials in production.
    * Create the necessary table by executing the following SQL command within your database:
        ```sql
        -- Connect to database: \c teo_db
        CREATE TABLE ventas_detalle (
            id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            id_producto VARCHAR(255) NOT NULL,
            fecha DATE NOT NULL,
            cantidad_vendida INT NOT NULL,
            fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        -- Indexes for performance
        CREATE INDEX idx_producto ON ventas_detalle (id_producto);
        CREATE INDEX idx_fecha ON ventas_detalle (fecha);
        ```

## 7. Data Requirements

The system expects historical sales data containing, at minimum, the following information per transaction:
* **Product Identifier (SKU):** A unique string identifying the product.
* **Sale Date:** The date of the transaction (e.g., YYYY-MM-DD).
* **Quantity Sold:** The number of units sold (positive integer).

**Input File Handling:**
* **Excel Files (`Factura_Importacion_PLUS_*.xlsx`):** The system is configured to read these files directly. It automatically looks for a sheet named **`Detalle`** and extracts data from the columns named **`SKU`**, **`Fecha Venta`**, and **`Cantidad`**, renaming them internally to `id_producto`, `fecha`, and `cantidad_vendida`. Other columns and sheets are ignored.
* **CSV Files:** Alternatively, you can upload a CSV file that already contains the columns named exactly **`id_producto`**, **`fecha`**, and **`cantidad_vendida`**.

## 8. Running the Application

You need two separate terminals, both with the virtual environment activated (`source venv/bin/activate`).

1.  **Start the Backend (Flask API):**
    ```bash
    python -m backend.app
    ```
    *(The backend typically runs on `http://127.0.0.1:5000`)*
2.  **Start the Frontend (Streamlit UI):**
    ```bash
    streamlit run frontend/Inicio.py
    ```
    *(Streamlit will provide a URL, usually `http://localhost:8501`)*

Open the Streamlit URL in your browser to interact with the application.

## 9. End-to-End Test Workflow (Clean Run)

To perform a clean test run from scratch, simulating a fresh deployment or evaluation:

1.  **Clean Database Records:**
    * Connect to your PostgreSQL database (e.g., via `psql` or pgAdmin).
    * Execute:
        ```sql
        TRUNCATE TABLE ventas_detalle RESTART IDENTITY CASCADE;
        ```

2.  **Clear Old Artifacts/Models:**
    * In your project's root directory via terminal:
        * **Mac/Linux:** `rm -rf models/*`
        * **Windows (cmd):** `del /Q models\*` (If this gives errors due to folders, use `rmdir /S /Q models` then `mkdir models`)
3.  **Clear Python Cache:**
    * In your project's root directory via terminal:
        * **Mac/Linux:** `find . -type d -name "__pycache__" -exec rm -r {} +`
        * **Windows (cmd):** `for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"`
4.  **Ensure Backend & Frontend are Running:** Use the commands from Section 8 (run backend first, then frontend).
5.  **Load Data:**
    * Navigate to the "Carga de Datos Históricos" page in the Streamlit UI.
    * Upload a valid data file (e.g., `Factura_Importacion_PLUS_2024.xlsx`, the synthetic `ventas_sinteticas_detalle_completo.csv`, or your consolidated `Ventas_Transaccionales_2020_2024.xlsx`).
    * Click "Procesar y Guardar en Base de Datos". Verify the success message and the number of rows saved.
6.  **Train Models:**
    * **Stop the backend server** (Ctrl+C in its terminal). This is important as training modifies files the backend might use.
    * Run the training script in the backend's terminal:
        ```bash
        python -m backend.ml_core.training
        ```
    * Wait for the training to complete. Check the output for evaluation metrics (MAE, RMSE, R²) and confirmation that `xgboost_model.joblib` and `mlp_model.keras` were saved in the `models/` directory.
7.  **Restart Backend:**
    * Restart the backend server in its terminal. This ensures it loads the *newly trained* artifacts into memory:
        ```bash
        python -m backend.app
        ```
8.  **Test Prediction:**
    * Go back to the Streamlit UI (refresh the page if necessary).
    * Navigate to the "Visualización de Predicción" page.
    * Enter an `id_producto` (SKU) that you know exists in the data you loaded (e.g., `SKU-2021-00010-3398` if using the sample data). Choose a future date.
    * Click "Generar Predicción de Unidades".
    * Verify that a prediction (in units) is displayed along with the historical sales chart for that specific SKU. Test with a non-existent SKU to verify error handling (should show a 404 error).

## 10. Prediction Flow Explanation

For a detailed step-by-step technical explanation of how a prediction request flows through the system (from user input in Streamlit, through the Flask API, preprocessing in `predict.py`, model inference, and back to the UI), please refer to the document: [`docs/Explicacion_Prediccion_MVP.md`](docs/Explicacion_Prediccion_MVP.md).

## 11. Future Work & Potential Improvements

* **Hyperparameter Tuning:** Systematically optimize XGBoost and MLP parameters (e.g., using `GridSearchCV` or `RandomizedSearchCV`) to potentially improve prediction accuracy (reduce MAE/RMSE, increase R²).
* **Feature Engineering:** Incorporate additional relevant features if available, such as:
    * **Temporal:** Holidays, promotional periods, day of the month/year.
    * **Product:** Product lifecycle stage, price changes.
    * **External:** Economic indicators, competitor activities.
* **Advanced Models:** Explore more sophisticated time-series models (e.g., ARIMA, SARIMA, Prophet, LSTM networks) especially for high-volume SKUs with sufficient historical data.
* **Seasonality Handling:** Implement techniques to explicitly model seasonal patterns if visual analysis or domain knowledge suggests their presence.
* **Error Handling & Logging:** Enhance robustness with more specific error catching and implement structured logging for better monitoring and debugging.
* **Deployment:** Containerize the application (Backend API and Frontend UI) using Docker for easier and more consistent deployment across different environments.
* **Confidence Intervals:** Enhance predictions by providing confidence intervals (e.g., using bootstrapping or quantile regression) to give users a sense of the prediction uncertainty.
* **Data Validation:** Implement more rigorous data validation checks during the upload process (e.g., using libraries like `Pandera` or `Great Expectations`).

-----

*This project was developed as part of the Systems Engineering program at Universidad Peruana de Ciencias Aplicadas (UPC).*