from flask import Flask, render_template, jsonify, request
import pandas as pd
import sqlite3
import os

app = Flask(__name__)

main_data_bases = [
	"./exel_data/Establecimientos_Ensenada_BJCA.xlsx",
	"./exel_data/Establecimientos_Mexicali_BJCA.xlsx",
	"./exel_data/Establecimientos_Playas_de_Rosarito_BJCA.xlsx"
	"./exel_data/Establecimientos_San_Felipe_BJCA.xlsx",
	"./exel_data/Establecimientos_San_Quintin_BJCA.xlsx",
	"./exel_data/Establecimientos_Tecate_BJCA.xlsx",
	"./exel_data/Establecimientos_Tijuana_BJCA.xlsx",
]
backup_data_bases = [
	"./sqlite_data/Ensenada_Baja_California.db",
	"./sqlite_data/Mexicali_Baja_California.db",
	"./sqlite_data/Playas_de_Rosarito_Baja_California.db",
	"./sqlite_data/San_Felipe_Baja_California.db",
	"./sqlite_data/San_Quintin_Baja_California.db",
	"./sqlite_data/Tecate_Baja_California.db",
	"./sqlite_data/Tijuana_Baja_California.db",
]
using_data_base = None


@app.route("/")
def working():
	return jsonify({
		"success": True,
		"message": "App up and runing!"
	})
@app.route("/api/exel/negocios/municipio", methods=['GET'])
def municipio():
    municipio = request.args.get('municipio')

    if not municipio:
        return jsonify({
            "success": False,
            "message": "Error: Municipio parameter is required. Use ?municipio=ensenada"
        }), 400

    try:
        
        match municipio.lower():
            case "ensenada":
                if os.path.exists(main_data_bases[0]):
                    df_actividades = pd.read_excel(main_data_bases[0])
                    using_data_base = df_actividades
                else:
                    conn = sqlite3.connect(backup_data_bases[0])
                    using_data_base = conn
            case "mexicali":
                if os.path.exists(main_data_bases[1]):
                    df_actividades = pd.read_excel(main_data_bases[1])
                    using_data_base = df_actividades
                else:
                    conn = sqlite3.connect(backup_data_bases[1])
                    using_data_base = conn
            case "playas de rosarito" | "plays de rosarito":
                if os.path.exists(main_data_bases[2]):
                    df_actividades = pd.read_excel(main_data_bases[2])
                    using_data_base = df_actividades
                else:
                    conn = sqlite3.connect(backup_data_bases[2])
                    using_data_base = conn
            case "san felipe" | "san felige":
                if os.path.exists(main_data_bases[3]):
                    df_actividades = pd.read_excel(main_data_bases[3])
                    using_data_base = df_actividades
                else:
                    conn = sqlite3.connect(backup_data_bases[3])
                    using_data_base = conn
            case "san quintin":
                if os.path.exists(main_data_bases[4]):
                    df_actividades = pd.read_excel(main_data_bases[4])
                    using_data_base = df_actividades
                else:
                    conn = sqlite3.connect(backup_data_bases[4])
                    using_data_base = conn
            case "tecate":
                if os.path.exists(main_data_bases[5]):
                    df_actividades = pd.read_excel(main_data_bases[5])
                    using_data_base = df_actividades
                else:
                    conn = sqlite3.connect(backup_data_bases[5])
                    using_data_base = conn
            case "tijuana":
                if os.path.exists(main_data_bases[6]):
                    df_actividades = pd.read_excel(main_data_bases[6])
                    using_data_base = df_actividades
                else:
                    conn = sqlite3.connect(backup_data_bases[6])
                    using_data_base = conn
            case _:
                return jsonify({
                    "success": False,
                    "message": f"Error: Municipio '{municipio}' not found"
                }), 404
        return jsonify({
            "success": True,
            "message": "Municipio encontrado exitosamente",
	    "municipio": municipio
        }),200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error processing request: {str(e)}"
        }), 500
@app.route("/api/exel/negocios/<string:word>", methods=['GET'])
def search(word):
	if len(word) < 4:
		return jsonify({
			"success": False,
			"message": "The search word needs to be equal or greater than four"
		}),400
	return jsonify({
		"success": True,
		"message": "Companys found succesuly",
		"data": word
	})

@app.route("/api/exel/fecha", methods=['GET'])
def filter_search():
    fecha = request.args.get('date')
    
    if not fecha:
        return jsonify({
	    "success": False,
	    "message": "Error: Date parameter is rquired. Use ?date=YYY/MM/DD"
        }),400

    if len(fecha) != 10 or fecha.count('/') != 2:
        return jsonify({
                "success": False,
                "message": "Error: Date format: YYY/MM/DD"
        }),400
    data = ["jose"]
    return jsonify({
        "success": True,
        "message": "Companys found succesfuly by date filter",
        "data": data
    })
