import fs from 'fs';
import http from 'http';
import path from 'path';

import { ContainerOutput } from './container-runner.js';
import { HA_API_KEY, HA_API_PORT, GROUPS_DIR } from './config.js';
import { logger } from './logger.js';
import { RegisteredGroup } from './types.js';

const HA_JID = 'ha:voice';
const HA_FOLDER = 'ha_voice';

export const HA_GROUP: RegisteredGroup = {
  name: 'Home Assistant Voice',
  folder: HA_FOLDER,
  trigger: '',
  added_at: new Date().toISOString(),
  requiresTrigger: false,
  isMain: false,
};

type RunAgentFn = (
  group: RegisteredGroup,
  prompt: string,
  chatJid: string,
  images?: Array<{ base64: string; mimeType: string }>,
  onOutput?: (output: ContainerOutput) => Promise<void>,
) => Promise<'success' | 'error'>;

function ensureHaGroupDir(): void {
  fs.mkdirSync(path.join(GROUPS_DIR, HA_FOLDER, 'logs'), { recursive: true });
}

export function startApiServer(runAgentFn: RunAgentFn): void {
  if (!HA_API_KEY) {
    logger.info('HA_API_KEY not set — Home Assistant API disabled');
    return;
  }

  ensureHaGroupDir();

  const server = http.createServer((req, res) => {
    if (req.method !== 'POST' || req.url !== '/chat') {
      res.writeHead(404);
      res.end();
      return;
    }

    let body = '';
    req.on('data', (chunk) => (body += chunk));
    req.on('end', async () => {
      try {
        const data = JSON.parse(body);

        if (data.api_key !== HA_API_KEY) {
          res.writeHead(401);
          res.end(JSON.stringify({ error: 'Unauthorized' }));
          return;
        }

        const text = (data.text || '').trim();
        if (!text) {
          res.writeHead(400);
          res.end(JSON.stringify({ error: 'text is required' }));
          return;
        }

        logger.info({ text: text.slice(0, 100) }, 'HA voice request');

        // Resolve HTTP as soon as agent produces a success/error result —
        // don't wait for the container to exit (it stays alive for idle timeout).
        const responses: string[] = [];
        let resolveHttp!: (text: string) => void;
        const httpPromise = new Promise<string>((r) => {
          resolveHttp = r;
        });

        // Run agent without awaiting — resolve HTTP on first final status
        void runAgentFn(
          HA_GROUP,
          text,
          HA_JID,
          undefined,
          async (output: ContainerOutput) => {
            if (output.result) {
              const raw =
                typeof output.result === 'string'
                  ? output.result
                  : JSON.stringify(output.result);
              const clean = raw
                .replace(/<internal>[\s\S]*?<\/internal>/g, '')
                .trim();
              if (clean) responses.push(clean);
            }
            if (output.status === 'success' || output.status === 'error') {
              resolveHttp(responses.join('\n\n') || 'No response.');
            }
          },
        ).catch((err) => {
          logger.error({ err }, 'HA agent error');
          resolveHttp('Sorry, an error occurred.');
        });

        // 90s timeout in case agent never sends a final status
        const responseText = await Promise.race([
          httpPromise,
          new Promise<string>((r) =>
            setTimeout(() => r('Request timed out.'), 90000),
          ),
        ]);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ response: responseText }));
      } catch (err) {
        logger.error({ err }, 'HA API error');
        res.writeHead(500);
        res.end(JSON.stringify({ error: 'Internal error' }));
      }
    });
  });

  server.listen(HA_API_PORT, '0.0.0.0', () => {
    logger.info({ port: HA_API_PORT }, 'Home Assistant API listening');
  });
}
