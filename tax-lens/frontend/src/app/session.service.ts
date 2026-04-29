import { Injectable, signal } from '@angular/core';
import { ChatMessage } from './tax.types';

/**
 * Session memory for the chat. Mirrors what the backend persists in MongoDB,
 * but kept locally for instant rendering. session_id is stable for the
 * browser tab lifetime so the backend can fetch the persistent history.
 */
@Injectable({ providedIn: 'root' })
export class SessionService {
  readonly sessionId = this.generateSessionId();
  readonly messages = signal<ChatMessage[]>([]);
  readonly selectedCompany = signal<string | null>(null);
  readonly isThinking = signal<boolean>(false);

  private generateSessionId(): string {
    const stored = sessionStorage.getItem('tax_lens_session_id');
    if (stored) return stored;
    const id = 'sess_' + crypto.randomUUID();
    sessionStorage.setItem('tax_lens_session_id', id);
    return id;
  }

  addMessage(msg: ChatMessage) {
    this.messages.update((m) => [...m, msg]);
  }

  reset() {
    this.messages.set([]);
    sessionStorage.removeItem('tax_lens_session_id');
  }
}
