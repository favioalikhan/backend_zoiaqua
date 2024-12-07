import PostgresAdapter from '@bot-whatsapp/database/postgres';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

// Simular __dirname en ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Cargar el archivo .env desde la carpeta raíz
dotenv.config({ path: path.resolve(__dirname, '../../../.env') });

// Validar que la variable DATABASE_URL esté definida
if (!process.env.DATABASE_URL) {
    console.error("❌ Error: La variable DATABASE_URL no está definida en el archivo .env.");
    process.exit(1);
}

export default new PostgresAdapter({
    connectionString: process.env.DATABASE_URL,
});
