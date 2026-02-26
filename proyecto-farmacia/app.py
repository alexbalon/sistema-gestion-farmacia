from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

# --- 1. CREACIÓN AUTOMÁTICA DE LA BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('farmacia.db')
    c = conn.cursor()
    
    # Crear Tablas
    c.execute('''CREATE TABLE IF NOT EXISTS Medicamento
                 (idMedicamento INTEGER PRIMARY KEY, nombre TEXT, lote TEXT, 
                  fechaCaducidad TEXT, stock INTEGER, precio REAL, esPsicotropico BOOLEAN)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Receta
                 (idReceta INTEGER PRIMARY KEY AUTOINCREMENT, registroMedico TEXT, 
                  nombrePaciente TEXT, idMedicamento INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Venta
                 (idVenta INTEGER PRIMARY KEY AUTOINCREMENT, total REAL, 
                  estadoSRI TEXT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Insertar inventario inicial (si está vacía)
    c.execute("SELECT COUNT(*) FROM Medicamento")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO Medicamento VALUES (1, 'Paracetamol 500mg', 'L-001', '2026-12-31', 100, 1.50, 0)")
        c.execute("INSERT INTO Medicamento VALUES (45, 'Diazepam 5mg (Controlado)', 'L-045', '2026-08-15', 50, 5.00, 1)")
        # La Amoxicilina caduca pronto para probar la alerta automática
        c.execute("INSERT INTO Medicamento VALUES (1045, 'Amoxicilina 500mg', 'L-1045', '2026-03-10', 45, 3.50, 0)")
        conn.commit()
    conn.close()

# Ejecutamos la función para que nazca la BD
init_db()


# --- 2. RUTAS DE LAS PANTALLAS ---
@app.route('/')
def punto_venta():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


# --- 3. RUTAS DE LOS CASOS DE USO (LÓGICA) ---
@app.route('/api/auditoria', methods=['GET'])
def auditar_caducidad():
    """Caso de Uso: Auditoría Automática de Caducidad"""
    conn = sqlite3.connect('farmacia.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # En SQLite calculamos la diferencia de días usando julianday
    c.execute('''SELECT *, CAST((julianday(fechaCaducidad) - julianday('now')) AS INTEGER) as dias_restantes 
                 FROM Medicamento 
                 WHERE dias_restantes <= 60''')
    alertas = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(alertas)

@app.route('/api/procesar_venta', methods=['POST'])
def procesar_venta():
    """Caso de Uso: Facturación y Validación de Receta"""
    data = request.json
    total = data.get('total')
    receta = data.get('receta')
    
    conn = sqlite3.connect('farmacia.db')
    c = conn.cursor()
    
    try:
        # Registrar Venta (Simula SRI)
        c.execute("INSERT INTO Venta (total, estadoSRI) VALUES (?, ?)", (total, 'AUTORIZADO-SRI'))
        
        # Estrategia Min-Min: Registrar Receta
        if receta and receta.get('medico'):
            c.execute("INSERT INTO Receta (registroMedico, nombrePaciente, idMedicamento) VALUES (?, ?, ?)", 
                      (receta['medico'], receta['paciente'], 45))
        
        # Descontar stock del psicotrópico
        c.execute("UPDATE Medicamento SET stock = stock - 1 WHERE idMedicamento = 45")
        
        conn.commit()
        return jsonify({"status": "success", "mensaje": "Venta procesada exitosamente.\nAutorización SRI: 092834710293"})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "mensaje": str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)