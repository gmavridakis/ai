import { Component, OnDestroy, OnInit } from '@angular/core';

interface Row { id: number; host: string; cpu: number; updated: string; }

@Component({
  selector: 'app-dashboard',
  template: `
    <h1>Hosts ({{ rows.length }})</h1>
    <table>
      @for (r of rows; track r.id) {
        <tr><td>{{ r.host }}</td><td>{{ r.cpu }}%</td><td>{{ r.updated }}</td></tr>
      }
    </table>
  `,
})
export class Dashboard implements OnInit, OnDestroy {
  rows: Row[] = [];
  private socket?: WebSocket;

  ngOnInit() {
    this.socket = new WebSocket('wss://ops.example.com/metrics');
    this.socket.onmessage = (event) => {
      this.rows = JSON.parse(event.data) as Row[];
    };
  }

  ngOnDestroy() { this.socket?.close(); }
}
