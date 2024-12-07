import BotWhatsapp from '@bot-whatsapp/bot';

/**
 * Un flujo conversacion que responder a las palabras claves "hola", "buenas", ...
 */
export default BotWhatsapp.addKeyword(['hola', 'buenas'])
    .addAnswer('Bienvenido a la tienda *Zoi Aqua*. ¿En qué puedo ayudarte 😀?')

