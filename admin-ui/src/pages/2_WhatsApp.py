"""WhatsApp connection page. Per D-01 (adapted) and D-02.

D-01 adapted: Using Evolution API REST endpoint /instance/connect/{instance}
instead of manager iframe. The Manager UI is a separate Docker container
(evolution-manager-v2, port 3000) NOT bundled in atendai/evolution-api:v2.2.3.
The REST approach is simpler and avoids an extra container.
"""
import streamlit as st
from components.evolution_api import EvolutionAPIClient, EvolutionAPIError

st.title("Conectar WhatsApp")

client = EvolutionAPIClient()

# Check current connection state
try:
    state = client.get_connection_state()
except EvolutionAPIError as e:
    if e.status_code == 404:
        state = "not_created"
    else:
        st.error(f"Error al verificar estado: {e.message}")
        st.stop()
except Exception:
    st.error("No se pudo conectar con Evolution API. Verifica que el servicio este activo.")
    st.stop()

if state == "open":
    st.success("WhatsApp esta conectado y funcionando.")
    st.info(
        "Si necesitas reconectar, desconecta primero desde la app de WhatsApp "
        "y recarga esta pagina."
    )
    st.stop()

# Instance may not exist yet (Pitfall 2)
if state == "not_created":
    st.warning("La instancia de WhatsApp no existe. Creando...")
    try:
        result = client.create_instance()
        st.success("Instancia creada exitosamente.")
        # create_instance with qrcode=True returns QR in response
        qr_base64 = result.get("qrcode", {}).get("base64", "")
        if qr_base64:
            st.markdown("### Escanea el codigo QR con WhatsApp")
            st.image(
                qr_base64,
                caption="Abre WhatsApp > Menu > Dispositivos vinculados > Vincular dispositivo",
            )
            st.info("El codigo QR se actualiza automaticamente. Recarga la pagina si expira.")
            st.stop()
    except EvolutionAPIError as e:
        st.error(f"Error al crear instancia: {e.message}")
        st.stop()

# Instance exists but not connected -- get QR
# D-01 adapted: Using REST API /instance/connect/{instance} instead of manager iframe
# (Manager UI is a separate container not bundled in evolution-api:v2.2.3)
st.markdown("### Escanea el codigo QR con WhatsApp")
st.markdown(
    "Abre **WhatsApp** > **Menu (tres puntos)** > "
    "**Dispositivos vinculados** > **Vincular dispositivo**"
)

try:
    qr_base64 = client.get_qr_code()
    if qr_base64:
        st.image(qr_base64, caption="Escanea este codigo con tu telefono")
    else:
        st.warning("No se pudo obtener el codigo QR. Intenta recargar la pagina.")
except EvolutionAPIError as e:
    st.error(f"Error al obtener QR: {e.message}")

st.markdown("---")
st.caption(
    "Despues de escanear, la pagina se actualizara automaticamente "
    "en el proximo ciclo de verificacion (60 segundos)."
)

# Manual refresh button
if st.button("Verificar conexion ahora"):
    st.session_state["wa_last_check"] = 0  # Force re-poll in sidebar
    st.rerun()
