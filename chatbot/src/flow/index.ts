import BotWhatsapp from '@bot-whatsapp/bot';
import chatbotFlow from './chatbot.flow';
import helloFlow from './hello.flow';
import welcomeFlow from './welcome.flow';

/**
 * Debes de implementasr todos los flujos
 */
export default BotWhatsapp.createFlow(
    [
        helloFlow,
        welcomeFlow,
        chatbotFlow
        
    ]
)