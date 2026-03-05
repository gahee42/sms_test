import { Controller, Post, Get, Body } from '@nestjs/common';
import { SmsService } from './sms.service';

@Controller('v1/sms')
export class SmsController {
  constructor(private readonly smsService: SmsService) {}

  @Post()
  receive(@Body() body: { raw: Record<string, unknown> }) {
    this.smsService.save(body.raw);
    return { status: 'ok' };
  }

  @Get()
  list() {
    return this.smsService.getAll();
  }
}
