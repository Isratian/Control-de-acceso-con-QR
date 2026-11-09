from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sqlite3
import qrcode
import os

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def inicializar_db():
    conexion = sqlite3.connect("vehiculos.db")
    cursor = conexion.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_vehiculo TEXT NOT NULL,
            placa TEXT NOT NULL,
            color TEXT NOT NULL,
            unidad TEXT NOT NULL,
            sgop TEXT,
            num_estacionamiento TEXT NOT NULL,
            telefono TEXT,
            qr_code TEXT,
            fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        cursor.execute("ALTER TABLE vehiculos ADD COLUMN telefono TEXT")
    except sqlite3.OperationalError:
        pass
        
    conexion.commit()
    conexion.close()

inicializar_db()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    conexion = sqlite3.connect("vehiculos.db")
    cursor = conexion.cursor()
    # Mostramos ordenados del más reciente al más antiguo, o como prefieras
    cursor.execute("SELECT id, tipo_vehiculo, placa, color, unidad, sgop, num_estacionamiento, telefono, qr_code, fecha_registro FROM vehiculos ORDER BY id DESC")
    filas = cursor.fetchall()
    conexion.close()
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"vehiculos": filas}
    )

@app.post("/registrar")
async def registrar_vehiculo(
    request: Request,
    tipo_vehiculo: str = Form(...),
    placa: str = Form(...),
    color: str = Form(...),
    unidad: str = Form(...),
    sgop: str = Form(""),
    num_estacionamiento: str = Form(...),
    telefono: str = Form("")
):
    placa_limpia = placa.strip().upper()
    vehiculo_limpio = tipo_vehiculo.strip()
    
    try:
        conexion = sqlite3.connect("vehiculos.db")
        cursor = conexion.cursor()
        
        cursor.execute("""
            INSERT INTO vehiculos (tipo_vehiculo, placa, color, unidad, sgop, num_estacionamiento, telefono)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (vehiculo_limpio, placa_limpia, color, unidad, sgop, num_estacionamiento, telefono))
        
        vehiculo_id = cursor.lastrowid
        
        datos_qr = f"Placa: {placa_limpia} | Vehículo: {vehiculo_limpio} | Color: {color} | Unidad: {unidad} | SGOP: {sgop} | Estacionamiento: {num_estacionamiento} | Tlf: {telefono}"
        img = qrcode.make(datos_qr)
        os.makedirs("static/qrs", exist_ok=True)
        qr_path = f"static/qrs/qr_{vehiculo_id}.png"
        img.save(qr_path)
        
        cursor.execute("UPDATE vehiculos SET qr_code = ? WHERE id = ?", (qr_path, vehiculo_id))
        conexion.commit()
        conexion.close()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar: {str(e)}")
    
    return RedirectResponse(url="/", status_code=303)

@app.get("/eliminar/{vehiculo_id}")
def eliminar_vehiculo(vehiculo_id: int):
    conexion = sqlite3.connect("vehiculos.db")
    cursor = conexion.cursor()
    
    cursor.execute("SELECT qr_code FROM vehiculos WHERE id = ?", (vehiculo_id,))
    fila = cursor.fetchone()
    if fila and fila[0] and os.path.exists(fila[0]):
        try:
            os.remove(fila[0])
        except:
            pass
            
    cursor.execute("DELETE FROM vehiculos WHERE id = ?", (vehiculo_id,))
    
    # Verificamos si la tabla se quedó completamente vacía
    cursor.execute("SELECT COUNT(*) FROM vehiculos")
    total = cursor.fetchone()[0]
    
    if total == 0:
        # Si no queda ningún registro, reiniciamos el contador autoincrementable de SQLite a 0
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='vehiculos'")
        
    conexion.commit()
    conexion.close()
    
    return RedirectResponse(url="/", status_code=303)

@app.get("/editar/{vehiculo_id}", response_class=HTMLResponse)
def editar_form(request: Request, vehiculo_id: int):
    conexion = sqlite3.connect("vehiculos.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT id, tipo_vehiculo, placa, color, unidad, sgop, num_estacionamiento, telefono, qr_code, fecha_registro FROM vehiculos WHERE id = ?", (vehiculo_id,))
    vehiculo = cursor.fetchone()
    conexion.close()
    
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
        
    return templates.TemplateResponse(
        request=request,
        name="editar.html",
        context={"vehiculo": vehiculo}
    )

@app.post("/actualizar/{vehiculo_id}")
async def actualizar_vehiculo(
    vehiculo_id: int,
    tipo_vehiculo: str = Form(...),
    placa: str = Form(...),
    color: str = Form(...),
    unidad: str = Form(...),
    sgop: str = Form(""),
    num_estacionamiento: str = Form(...),
    telefono: str = Form("")
):
    placa_limpia = placa.strip().upper()
    vehiculo_limpio = tipo_vehiculo.strip()
    
    try:
        conexion = sqlite3.connect("vehiculos.db")
        cursor = conexion.cursor()
        
        datos_qr = f"Placa: {placa_limpia} | Vehículo: {vehiculo_limpio} | Color: {color} | Unidad: {unidad} | SGOP: {sgop} | Estacionamiento: {num_estacionamiento} | Tlf: {telefono}"
        img = qrcode.make(datos_qr)
        os.makedirs("static/qrs", exist_ok=True)
        qr_path = f"static/qrs/qr_{vehiculo_id}.png"
        img.save(qr_path)
        
        cursor.execute("""
            UPDATE vehiculos 
            SET tipo_vehiculo = ?, placa = ?, color = ?, unidad = ?, sgop = ?, num_estacionamiento = ?, telefono = ?, qr_code = ?
            WHERE id = ?
        """, (vehiculo_limpio, placa_limpia, color, unidad, sgop, num_estacionamiento, telefono, qr_path, vehiculo_id))
        
        conexion.commit()
        conexion.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar: {str(e)}")
        
    return RedirectResponse(url="/", status_code=303)