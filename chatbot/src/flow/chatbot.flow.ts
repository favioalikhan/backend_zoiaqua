// chatbot.flow.ts

import BotWhatsapp from '@bot-whatsapp/bot';
import axios from 'axios';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config({ path: path.resolve(__dirname, '../../../.env') });

const BACKEND_URL = process.env.BACKEND_URL;
const STORE_ADDRESS = process.env.STORE_ADDRESS || 'Jose Carlos Mariategui 451 Amarilis, Huánuco';
const CONFIRM_PAYMENT_TOKEN = process.env.CONFIRM_PAYMENT_TOKEN; 

export default BotWhatsapp.addKeyword(BotWhatsapp.EVENTS.ACTION)
    .addAction(async (ctx, {state, flowDynamic}) => {
        const customerName = state.get('customer_name') || ''
        const customerLastName = state.get('customer_last_name') || ''
        const dni = state.get('dni')
        const telefono = ctx.from || '' // captando el telefono del cliente

        const items = state.get('items') || []
        if(items.length === 0){
            await flowDynamic('No has seleccionado productos. Por favor, vuelve a seleccionar productos antes de pagar.');
            return;
        }

        // Crear cliente
        try {
            const clienteResponse = await axios.post(`${BACKEND_URL}/clientes/`, {
                nombre: customerName,
                apellido_paterno: customerLastName,
                dni: dni,
                telefono: telefono,
                direccion: '',
                ciudad: ''
            })
            const cliente = clienteResponse.data;
            const cliente_id = cliente.id; // Ajusta según respuesta real

            // Crear pedido temporal
            const pedidoTempResponse = await axios.post(`${BACKEND_URL}/pedidos/create-temp/`, {
                cliente_id,
                items
            })
            const pedidoTemp = pedidoTempResponse.data.pedido
            await state.update({pedido_id: pedidoTemp.id})

            // Confirmar pedido
            const headers: any = {}
            if (CONFIRM_PAYMENT_TOKEN) {
                headers['Authorization'] = `Bearer ${CONFIRM_PAYMENT_TOKEN}`
            }

            const pedido_id = pedidoTemp.id
            const confirmResponse = await axios.post(`${BACKEND_URL}/pedidos/${pedido_id}/confirm-payment/`, {}, { headers })

            // Obtener detalles del pedido
            const pedidoDetail = await axios.get(`${BACKEND_URL}/pedidos/${pedido_id}`)
            const pedido = pedidoDetail.data

            // Obtener distribucion
            const distribucionResp = await axios.get(`${BACKEND_URL}/distribuciones/?pedido=${pedido_id}`)
            const distribucion = distribucionResp.data.results[0] || {}

            // Simular boleta (puedes personalizar)
            let boleta = `BOLETA DE PAGO\nCliente: ${customerName} ${customerLastName}\nDNI: ${dni}\nPedido ID: ${pedido_id}\nFecha salida: ${distribucion.fecha_salida}\nFecha entrega: ${distribucion.fecha_entrega}`

            // Mostrar boleta y mensaje de gracias
            await flowDynamic(boleta);
            await flowDynamic('¡Gracias por tu compra!');

        } catch (error) {
            console.log('Error al confirmar pedido:', error)
            await flowDynamic('Ocurrió un error al procesar tu pedido. Intenta más tarde.')
        }
    });
