import pickle
import pandas as pd
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'secret'

DATA_PATH = "model/data_jagung.csv"
MODEL_PATH = "model/model.pkl"

model = pickle.load(open(MODEL_PATH, "rb"))

USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"},
}

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = USERS.get(username)
        if user and user["password"] == password:
            session["username"] = username
            session["role"] = user["role"]
            flash(f"Selamat datang, {username}!", "success")

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("user_dashboard"))
        else:
            flash("Username atau password salah.", "danger")

    return render_template("login.html")

@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    if session.get("role") != "admin":
        flash("Akses hanya untuk admin!", "danger")
        return redirect(url_for("login"))

    if os.path.exists(DATA_PATH):
        data = pd.read_csv(DATA_PATH)
    else:
        data = pd.DataFrame(columns=[
            "TAHUN", "HASIL_PRODUKSI_KG",
            "KELEMBAPAN", "SUHU_RATA2",
            "LUAS_TANAH_M2", "CURAH_HUJAN"
        ])

    if request.method == "POST":
        try:
            new_data = {
                "TAHUN": int(request.form.get("tahun")),
                "HASIL_PRODUKSI_KG": float(request.form.get("hasil_produksi")),
                "KELEMBAPAN": float(request.form.get("kelembapan")),
                "SUHU_RATA2": float(request.form.get("suhu")),
                "LUAS_TANAH_M2": float(request.form.get("luas_tanah")),
                "CURAH_HUJAN": float(request.form.get("curah_hujan"))
            }
            data = pd.concat(
                [data, pd.DataFrame([new_data])], ignore_index=True)
            data.to_csv(DATA_PATH, index=False)
            flash("Data berhasil ditambahkan", "success")
        except Exception as e:
            flash(f"Error input data: {e}", "danger")

    return render_template(
        "admin_dashboard.html",
        table=data.to_html(
            classes='table-auto w-full text-sm text-center border border-collapse border-green-700',
            index=False,
            border=1
        )
    )

@app.route("/user", methods=["GET", "POST"])
def user_dashboard():
    if session.get("role") != "user":
        flash("Akses hanya untuk user!", "danger")
        return redirect(url_for("login"))

    df = pd.read_csv(DATA_PATH)
    historis_df = df.groupby("TAHUN")["HASIL_PRODUKSI_KG"].mean().reset_index()

    prediksi_list = session.get("prediksi_list", [])

    if request.method == "POST":
        try:
            tahun = float(request.form.get("tahun"))
            luas_tanah_m2 = float(request.form.get("luas_tanah"))
            curah_hujan = float(request.form.get("curah_hujan"))
            kelembapan = float(request.form.get("kelembapan"))
            suhu_rata2 = float(request.form.get("suhu"))

            df_input = pd.DataFrame(
                [[tahun, luas_tanah_m2, curah_hujan, kelembapan, suhu_rata2]],
                columns=["TAHUN", "LUAS_TANAH_M2", "CURAH_HUJAN", "KELEMBAPAN", "SUHU_RATA2"]
            )

            pred = model.predict(df_input)[0]
            prediction = round(pred, 2)

            prediksi_list.append(
                {"tahun": int(tahun), "hasil": prediction})
            session["prediksi_list"] = prediksi_list

        except Exception as e:
            flash(f"Error saat prediksi: {e}", "danger")
            prediction = None
    else:
        prediction = None

    chart_labels = historis_df["TAHUN"].astype(str).tolist()
    chart_data_historis = historis_df["HASIL_PRODUKSI_KG"].tolist()

    chart_data_prediksi = [None] * len(chart_labels)
    for pred in prediksi_list:
        if str(pred["tahun"]) in chart_labels:
            idx = chart_labels.index(str(pred["tahun"]))
            chart_data_prediksi[idx] = pred["hasil"]

    chart_label_historis = "Data Historis Panen (kg)"
    chart_label_prediksi = "Prediksi Panen Terbaru (kg)"

    return render_template(
        "user_dashboard.html",
        prediction=prediction,
        chart_labels=chart_labels,
        chart_data_historis=chart_data_historis,
        chart_data_prediksi=chart_data_prediksi,
        chart_label_historis=chart_label_historis,
        chart_label_prediksi=chart_label_prediksi,
    )

@app.route("/logout")
def logout():
    session.clear()
    flash("Berhasil logout", "success")
    return redirect(url_for("login"))

if __name__ == "__main__":
    if not os.path.exists("data"):
        os.makedirs("data")
    app.run(debug=True)
