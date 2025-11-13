from flask import Flask, render_template, jsonify, request
import pandas as pd

app = Flask(__name__)


@app.route("/")
def working():
	return jsonify({
		"success": True,
		"message": "App up and runing!"
	})

@app.route("/api/exel/negocio/<string:word>", methods=['GET'])
def search(word):
	if len(word) < 4:
		return jsonify({
			"success": False,
			"message": "The search word needs to be equal or greater than four"
		}),400
	#df_actividades = pd.read_excel('./exel_data/Establecimientos_Ensenada_BJCA.xlsx', sheet_name='actividades')
	#df_nombres = pd.read_excel('./exel_data/Establecimientos_Ensenada_BJCA.xlsx', sheet_name='nombres_establecimientos')
	return jsonify({
		"success": True,
		"message": "Company found!",
		"data": word
	})
