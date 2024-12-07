// gemini/index.ts
import { GoogleGenerativeAI } from "@google/generative-ai";
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { generatePrompt, generatePromptDetermine } from "./prompts";

// Simular __dirname en ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Cargar el archivo .env desde la carpeta raíz
dotenv.config({ path: path.resolve(__dirname, '../../../../.env') });

if (!process.env.GEMINI_API_KEY) {
    console.error("❌ Error: La variable GEMINI_API_KEY no está definida en el archivo .env.");
    process.exit(1);
}
// Tipado simplificado similar a ChatCompletionMessageParam:
type ChatMessage = {
  role: 'user' | 'assistant' | 'system',
  content: string
}

// Convertir ChatMessage[] a Content[] para Gemini
// Content es { role: 'user'|'model'|'system', parts: [{text:string}] }
function convertHistoryToContents(history: ChatMessage[]) {
  return history.map(msg => {
    let role: 'user' | 'model' | 'system' = 'user'
    if (msg.role === 'assistant') {
      role = 'model'
    } else if (msg.role === 'system') {
      role = 'system'
    } else if (msg.role === 'user') {
      role = 'user'
    }
    return {
      role: role,
      parts: [{ text: msg.content }]
    }
  })
}

const apiKey = process.env.GEMINI_API_KEY as string
if (!apiKey) {
  throw new Error('API_KEY no definido en las variables de entorno')
}

const genAI = new GoogleGenerativeAI(apiKey)
const model = genAI.getGenerativeModel({
  model: "gemini-1.5-flash",
  // Puedes agregar configuración aquí:
  generationConfig: {
    candidateCount: 1,
    maxOutputTokens: 800,
    temperature: 1.0
  }
})

/**
 * Similar a run() de OpenAI
 * @param name Nombre del cliente
 * @param lastname Apellido del cliente
 * @param question La pregunta del cliente
 * @param history Historial de la conversación
 */
export const run = async (name: string, lastname: string,question: string, history: ChatMessage[]): Promise<string> => {
  const prompt = generatePrompt(name, lastname, question)

  // Creamos el contenido inicial con el mensaje del sistema
  const systemContent = {
    role: 'system' as const,
    parts: [{ text: prompt }]
  }

  const contents = [systemContent, ...convertHistoryToContents(history)]

  const result = await model.generateContent({ contents })
  
  // Obtenemos el texto de la respuesta
  if (result?.response?.candidates?.[0]?.content?.parts?.length) {
    return result.response.candidates[0].content.parts.map(p => p.text).join(' ')
  }
  return 'No se pudo generar respuesta'
}

/**
 * Similar a runDetermine() de OpenAI
 * Analiza la conversación para identificar un producto
 * @param history Historial de la conversación
 * @returns ID del producto o 'unknown'
 */
export const runDetermine = async (history: ChatMessage[]): Promise<string> => {
  const prompt = generatePromptDetermine()

  const systemContent = {
    role: 'system' as const,
    parts: [{ text: prompt }]
  }

  const contents = [systemContent, ...convertHistoryToContents(history)]

  const result = await model.generateContent({ contents })

  if (result?.response?.candidates?.[0]?.content?.parts?.length) {
    const text = result.response.candidates[0].content.parts.map(p => p.text).join(' ')
    // Si el texto no corresponde a uno de los IDs esperados, devolvemos 'unknown'
    // Suponiendo que el modelo simplemente responde con el ID o 'unknown'
    if (text === 'AGUA625' || text === 'AGUA1L' || text === 'AGUA20L' || text === 'unknown') {
      return text
    }
  }
  return 'unknown'
}
