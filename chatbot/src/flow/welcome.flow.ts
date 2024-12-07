import BotWhatsapp from '@bot-whatsapp/bot';
import axios from 'axios';
import dotenv from 'dotenv';
import path from 'path';
import { run, runDetermine } from 'src/services/gemini';
import { fileURLToPath } from 'url';
import chatbotFlow from './chatbot.flow';

// Simular __dirname en ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Cargar el archivo .env desde la carpeta raíz
dotenv.config({ path: path.resolve(__dirname, '../../../.env') });
const BACKEND_URL = process.env.BACKEND_URL;

interface MessageParam {
    role: 'system' | 'user';
    content: string;
}

export default BotWhatsapp.addKeyword(BotWhatsapp.EVENTS.WELCOME)
    .addAction(async (ctx, { state, flowDynamic }) => {
        const history = (state.getMyState()?.history ?? []) as MessageParam[];

        // Añadir contexto inicial si no existe
        if (history.length === 0) {
            history.push({
                role: 'system',
                content: 'Eres un asistente de ventas para una tienda de agua mineral. Ayuda a los clientes a comprar agua, mostrar catálogo y procesar pedidos.'
            });
        }

        // Agregar el mensaje del usuario al historial
        history.push({
            role: 'user',
            content: ctx.body || 'Iniciar conversación'
        });

        await state.update({ history });

        const chatHistory = history.map(h => ({role: h.role, content: h.content})) as {role:'user'|'assistant'|'system', content:string}[];

        // Intentar determinar la intención del cliente usando runDetermine (opcional)
        const intent = await runDetermine(chatHistory);
        console.log(`[INTENT DETECTADO]: ${intent}`);

        // Verificar si tenemos el nombre y apellido paterno
        const customerName = state.get('customer_name') || '';
        const customerLastName = state.get('customer_last_name') || '';

        if (!customerName) {
            await flowDynamic('Para comenzar, ¿podrías proporcionarme tu nombre?');
            await state.update({ esperandoNombre: true });
            return;
        }

        if (customerName && !customerLastName) {
            await flowDynamic(`Genial ${customerName}, ahora necesito tu apellido paterno:`);
            await state.update({ esperandoApellido: true });
            return;
        }

        // Si ya tenemos nombre y apellido, podemos dar una respuesta generada por Gemini
        const preguntaDelCliente = ctx.body.trim() || 'Necesito información';
        const assistantResponse = await run(customerName, customerLastName, preguntaDelCliente, chatHistory);

        const responseChunks = assistantResponse.split(/(?<!\d)\.\s+/g);
        for (const chunk of responseChunks) {
            await flowDynamic(chunk);
        }

        // Mostrar el catálogo de productos
        await mostrarProductosDisponibles(flowDynamic, state);
        await state.update({ esperandoProducto: true });
    })

    // Capturar nombre
    .addAnswer('', { capture: true }, async (ctx, { state, flowDynamic, fallBack }) => {
        const esperandoNombre = state.get('esperandoNombre');
        if (!esperandoNombre) return;

        const nombre = ctx.body.trim();
        if (nombre.length < 2) {
            return fallBack('Necesito un nombre válido, inténtalo nuevamente.');
        }

        await state.update({ customer_name: nombre, esperandoNombre: false });
        await flowDynamic(`Genial ${nombre}, ahora necesito tu apellido paterno:`);
        await state.update({ esperandoApellido: true });
    })

    // Capturar apellido
    .addAnswer('', { capture: true }, async (ctx, { state, flowDynamic, fallBack }) => {
        const esperandoApellido = state.get('esperandoApellido');
        if (!esperandoApellido) return;

        const apellido = ctx.body.trim();
        if (apellido.length < 2) {
            return fallBack('Necesito un apellido paterno válido, inténtalo nuevamente.');
        }

        const nombre = state.get('customer_name');
        await state.update({ customer_last_name: apellido, esperandoApellido: false });

        await flowDynamic(`Perfecto ${nombre} ${apellido}, ahora te mostraré nuestros productos disponibles.`);
        await mostrarProductosDisponibles(flowDynamic, state);
        await state.update({ esperandoProducto: true });
    })

    // Capturar selección de producto
    .addAnswer('', { capture: true }, async (ctx, { state, flowDynamic, fallBack }) => {
        const esperandoProducto = state.get('esperandoProducto');
        if (!esperandoProducto) return;

        const seleccion = ctx.body.trim().toLowerCase();
        let productos = state.get('productosDisponibles') || [];

        if (productos.length === 0) {
            const response = await axios.get(`${BACKEND_URL}/productos/disponibles/`);
            productos = response.data;
            await state.update({productosDisponibles: productos});
        }

        const index = parseInt(seleccion, 10) - 1;
        if (isNaN(index) || index < 0 || index >= productos.length) {
            return fallBack('Opción inválida. Por favor, elige una opción válida según el número mostrado.');
        }

        const productoSeleccionado = productos[index];
        await state.update({productoSeleccionado});
        await flowDynamic(`Has seleccionado: ${productoSeleccionado.nombre}. Ahora ingresa la cantidad que deseas:`);
        await state.update({ esperandoProducto: false, esperandoCantidad: true });
    })

    // Capturar cantidad y verificar stock
    .addAnswer('', { capture: true }, async (ctx, { state, flowDynamic, fallBack }) => {
        const esperandoCantidad = state.get('esperandoCantidad');
        if (!esperandoCantidad) return;

        const cantidadStr = ctx.body.trim();
        const cantidad = parseInt(cantidadStr, 10);

        if (isNaN(cantidad) || cantidad <= 0) {
            return fallBack('Por favor, introduce una cantidad válida (un número entero mayor que 0).');
        }

        const productoSeleccionado = state.get('productoSeleccionado');
        if (!productoSeleccionado) {
            await flowDynamic('No se ha seleccionado ningún producto. Vuelve a elegir uno.');
            await mostrarProductosDisponibles(flowDynamic, state);
            await state.update({ esperandoProducto: true, esperandoCantidad: false });
            return;
        }

        try {
            const response = await axios.post(`${BACKEND_URL}/productos/check-stock/`, {
                producto_id: productoSeleccionado.id,
                cantidad
            });
            const stock = response.data;

            if (!stock.disponible) {
                await flowDynamic(`Lo siento, no hay suficiente stock para la cantidad solicitada. ${stock.mensaje}`);
                await mostrarProductosDisponibles(flowDynamic, state);
                await state.update({ esperandoProducto: true, esperandoCantidad: false });
                return;
            }

            const items = state.get('items') || [];
            items.push({
                producto_id: productoSeleccionado.id,
                cantidad,
                precio_unitario: stock.precio_unitario,
                subtotal: stock.total
            });

            await state.update({items, esperandoCantidad: false, productoSeleccionado: null});

            await flowDynamic(`Cantidad confirmada: ${cantidad} de ${productoSeleccionado.nombre}. Subtotal: S/${stock.total}. ¿Deseas agregar otro producto?\n1. Sí\n2. No`);
            await state.update({ esperandoMasProductos: true });

        } catch (error) {
            console.error(error);
            await flowDynamic('Hubo un error al verificar el stock. Por favor, intenta nuevamente.');
            await mostrarProductosDisponibles(flowDynamic, state);
            await state.update({ esperandoProducto: true, esperandoCantidad: false });
        }
    })

    // Capturar si desea agregar más productos o no
    .addAnswer('', { capture: true }, async (ctx, { state, flowDynamic, fallBack, gotoFlow }) => {
        const esperandoMasProductos = state.get('esperandoMasProductos');
        if (!esperandoMasProductos) return;

        const respuesta = ctx.body.trim().toLowerCase();
        if (respuesta.includes('1') || respuesta.includes('si') || respuesta.includes('sí')) {
            await flowDynamic('De acuerdo, elige otro producto del catálogo:');
            await mostrarProductosDisponibles(flowDynamic, state);
            await state.update({ esperandoProducto: true, esperandoMasProductos: false });
        } else if (respuesta.includes('2') || respuesta.includes('no')) {
            // Calcular el total a pagar
            const items = state.get('items') || [];
            const total = items.reduce((acc: number, it: any) => acc + it.subtotal, 0);

            // Mostrar el total antes de preguntar tienda/delivery
            await flowDynamic(`El total a pagar por tu pedido es S/${total}. ¿Deseas recoger en tienda o delivery?\n1. Tienda\n2. Delivery`);
            await state.update({ esperandoMetodoEntrega: true, esperandoMasProductos: false });
        } else {
            return fallBack('Respuesta inválida. Responde "1" para sí o "2" para no.');
        }
    })

    // Capturar método de entrega
    .addAnswer('', { capture: true }, async (ctx, { state, flowDynamic, fallBack }) => {
        const esperandoMetodoEntrega = state.get('esperandoMetodoEntrega');
        if (!esperandoMetodoEntrega) return;

        const metodo = ctx.body.trim().toLowerCase();
        await state.update({ esperandoMetodoEntrega: false });

        const STORE_ADDRESS = process.env.STORE_ADDRESS;

        if (metodo.includes('1') || metodo.includes('tienda')) {
            await state.update({metodoEntrega: 'tienda', direccion: STORE_ADDRESS});
            // Una vez elegido el método, ahora sí mostramos el QR
            await flowDynamic([{
                body: 'Escanea el QR',
                media: 'https://example.com/qr-pago.png'
            }]);
            await flowDynamic('Una vez pagues, responde con "Sí" para continuar.');
            await state.update({ esperandoConfirmacionPago: true });
        } else if (metodo.includes('2') || metodo.includes('delivery')) {
            await state.update({metodoEntrega:'delivery'});
            await flowDynamic('Ingresa tu dirección completa (dirección, ciudad):');
            await state.update({ esperandoDireccion: true });
        } else {
            return fallBack('Opción inválida, elige "1" tienda o "2" delivery');
        }
    })

    // Capturar dirección si delivery
    .addAnswer('', { capture: true }, async (ctx, { state, flowDynamic, fallBack }) => {
        const esperandoDireccion = state.get('esperandoDireccion');
        if(!esperandoDireccion) return;

        const direccion = ctx.body.trim();
        if (direccion.length < 5) {
            return fallBack('La dirección es muy corta, necesito más detalles.');
        }

        await state.update({direccion, esperandoDireccion:false});
        // Mostrar el QR ahora que ya tenemos la dirección (para delivery)
        await flowDynamic([{
            body: 'Escanea el QR',
            media: 'https://example.com/qr-pago.png'
        }]);
        await flowDynamic('Una vez pagues, responde con "Sí" para continuar.');
        await state.update({ esperandoConfirmacionPago: true });
    })

    // Confirmación de pago ("Sí")
    .addAnswer('', { capture:true }, async (ctx, {state, flowDynamic, fallBack, gotoFlow}) => {
        const esperandoConfirmacionPago = state.get('esperandoConfirmacionPago');
        if(!esperandoConfirmacionPago) return;

        const respuesta = ctx.body.trim().toLowerCase();
        if (respuesta === 'sí' || respuesta === 'si') {
            // Ahora pedimos el DNI para emitir la boleta
            await flowDynamic('Perfecto, por favor dame tu DNI para emitir la boleta.');
            await state.update({ esperandoDNI: true });
        } else if (respuesta === 'no') {
            await flowDynamic('Entiendo, puedes pagar más tarde. Si deseas cancelar, escribe "cancelar".');
            await state.update({ pedidoPendiente:true });
        } else {
            return fallBack('No te he entendido, responde "Sí" si pagaste o "No" si todavía no.');
        }
    })

    // DNI, crear cliente, crear pedido, confirmar pedido en chatbot.flow
    // Aquí simplemente pasamos el control a chatbotFlow una vez obtengamos el DNI
    // Pero el DNI se pedirá aquí mismo:
    .addAnswer('', { capture:true }, async (ctx, {state, flowDynamic, fallBack, gotoFlow}) => {
        const esperandoDNI = state.get('esperandoDNI');
        if(!esperandoDNI) return;

        const dni = ctx.body.trim();
        if(!/^\d{8}$/.test(dni)){
            return fallBack('El DNI debe contener 8 dígitos numéricos, intenta nuevamente.');
        }

        await state.update({dni, esperandoDNI:false});
        // Ahora que tenemos DNI, iremos a chatbotFlow para crear cliente, pedido y confirmar
        return gotoFlow(chatbotFlow);
    })


async function mostrarProductosDisponibles(flowDynamic: Function, state:any) {
    const response = await axios.get(`${BACKEND_URL}/productos/disponibles/`);
    const productos = response.data;
    await state.update({productosDisponibles: productos});
    let mensaje = 'Productos disponibles:\n';
    productos.forEach((prod: any, index: number) => {
        mensaje += `${index+1}. ${prod.nombre} - Precio: S/${prod.precio_unitario}\n`;
    });
    await flowDynamic(mensaje);
}
