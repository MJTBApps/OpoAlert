# Ejecutor de OpoAlert en el ordenador de casa

Algunos boletines (Navarra, Asturias, Ceuta, y a ratos La Rioja y Cáceres) **no responden a los servidores de GitHub**, que están fuera de España, pero sí a una conexión española normal. El ordenador de casa, siempre encendido, hace solo esas lecturas: GitHub le avisa a las 6:50, 9:50, 12:50 y 16:50 (en invierno), el ordenador lee los boletines y devuelve el resultado, y GitHub lo valida y lo publica igual que el resto.

- No hace falta dejar ninguna sesión abierta ni tener nada a la vista: funciona como un servicio en segundo plano.
- Si el ordenador está apagado, esas fuentes simplemente no se actualizan esa vez; el resto de la app sigue igual.
- Solo ejecuta el workflow `revisar-espana-casa.yml` de este repositorio, nunca código de otras personas (ver el paso 1).

---

## En un Mac (recomendado)

### 1. Protección en GitHub (una sola vez, imprescindible)
El repositorio es público: hay que impedir que alguien de fuera pueda lanzar trabajos en tu ordenador.
1. En **github.com/MJTBApps/OpoAlert** → **Settings** → **Actions** → **General**.
2. En **«Approval for running fork pull request workflows from contributors»** elige **«Require approval for all external contributors»** y pulsa **Save**.

### 2. Python en el Mac
1. Descarga e instala **Python 3.12** desde https://www.python.org/downloads/macos/ (instalador «macOS 64-bit universal2»).
2. Abre la app **Terminal** y copia estas dos órdenes (una a una):
   ```
   python3.12 -m venv ~/opoalert-venv
   ~/opoalert-venv/bin/pip install requests beautifulsoup4 certifi cryptography pymupdf pypdf defusedxml tzdata
   ```

### 3. Instalar el ejecutor de GitHub
1. En **github.com/MJTBApps/OpoAlert** → **Settings** → **Actions** → **Runners** → botón verde **New self-hosted runner**.
2. Elige **macOS** y la arquitectura de tu Mac: **ARM64** si es Apple M1/M2/M3/M4, **x64** si es Intel ( → Acerca de este Mac).
3. GitHub te muestra unas órdenes en dos bloques, **Download** y **Configure**. Cópialas en Terminal una a una, tal cual.
   - Cuando la configuración pregunte **«Enter any additional labels»**, escribe: `opoalert-casa`
   - En el resto de preguntas pulsa Intro (valores por defecto).
   - **No ejecutes** el último `./run.sh` que propone GitHub: en su lugar haz el paso 4.
4. Dile al ejecutor dónde está Python (en la misma carpeta `actions-runner`):
   ```
   echo "OPOALERT_PYTHON=$HOME/opoalert-venv/bin/python" >> .env
   ```
5. Instálalo como servicio para que arranque solo con el Mac:
   ```
   ./svc.sh install
   ./svc.sh start
   ```
6. En GitHub, **Settings → Actions → Runners** debe aparecer el ejecutor en verde, **Idle**.

### 4. Que el Mac no se duerma
**Ajustes del Sistema** → **Energía** (o **Batería → Opciones** en un portátil):
- Activa **«Evitar que el ordenador entre en reposo automáticamente cuando la pantalla está apagada»**.
- Activa **«Arrancar automáticamente tras un corte de luz»** si aparece.
La pantalla puede apagarse; lo importante es que el ordenador no entre en reposo.

### 5. Probarlo
En **github.com/MJTBApps/OpoAlert** → **Actions** → **«OpoAlert - Revisar boletines desde el PC de casa»** → **Run workflow** → **Run workflow**. En unos minutos debe terminar en verde.

---

## En un PC con Windows (alternativa)
1. Paso 1 de arriba (protección en GitHub), igual.
2. Instala **Python 3.12** desde https://www.python.org/downloads/windows/ (marca «Add python.exe to PATH») y **Git for Windows** desde https://git-scm.com/download/win (lo necesita el ejecutor).
3. En **PowerShell**:
   ```
   py -3.12 -m venv $HOME\opoalert-venv
   & $HOME\opoalert-venv\Scripts\pip install requests beautifulsoup4 certifi cryptography pymupdf pypdf defusedxml tzdata
   ```
4. **New self-hosted runner** → **Windows** → **x64**, y sigue sus órdenes en PowerShell. Etiqueta adicional: `opoalert-casa`. Cuando pregunte **«Would you like to run the runner as service?»**, responde **Y**.
5. En la carpeta del ejecutor crea un archivo `.env` con esta línea (cambia TU_USUARIO):
   `OPOALERT_PYTHON=C:/Users/TU_USUARIO/opoalert-venv/Scripts/python.exe`
   y reinicia el servicio (o el ordenador).
6. **Configuración → Sistema → Inicio/apagado y suspensión**: «Suspender» → **Nunca** (con corriente).
7. Prueba como en el paso 5 del Mac.

---

## Si algo falla
- En **Actions**, abre la ejecución en rojo: el motivo aparece como anotación al principio de la página.
- Si el ejecutor sale **Offline** en Settings → Runners: el ordenador está apagado, dormido o sin red.
- Para quitarlo del todo: en el Mac, `./svc.sh stop`, `./svc.sh uninstall` y en GitHub **Settings → Runners → Remove**.
