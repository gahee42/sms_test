import { Injectable, Logger } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class SmsService {
  private readonly logger = new Logger(SmsService.name);
  private readonly logPath = path.join(process.cwd(), 'sms_log.jsonl');

  save(raw: Record<string, unknown>) {
    const entry = { raw, received_at: new Date().toISOString() };
    fs.appendFileSync(this.logPath, JSON.stringify(entry) + '\n');
    this.logger.log(`[저장] From:${raw?.Phone} Content:${raw?.Content}`);
  }

  getAll() {
    if (!fs.existsSync(this.logPath)) return [];
    return fs
      .readFileSync(this.logPath, 'utf-8')
      .trim()
      .split('\n')
      .filter(Boolean)
      .map((line) => JSON.parse(line));
  }
}
